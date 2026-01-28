# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""
Midtrans refund handler implementation.
"""

import frappe
from frappe import _
from typing import Dict, Any
import requests
import base64
from payments.refund.base import RefundHandler


class MidtransRefundHandler(RefundHandler):
	"""
	Refund handler for Midtrans payment gateway.
	
	Uses Midtrans Core API v2 for refund processing.
	API Docs: https://docs.midtrans.com/reference/refund-transaction
	"""
	
	def validate(self) -> bool:
		"""Validate Midtrans refund request."""
		# Check if we have gateway settings
		if not self.gateway_settings:
			frappe.throw(_("Midtrans Settings not found"))
		
		# Check if we have transaction ID
		transaction_id = self.get_transaction_id()
		if not transaction_id:
			frappe.throw(_("Transaction ID not found in payment data"))
		
		# Check transaction status with Midtrans
		status = self._get_transaction_status(transaction_id)
		
		if not status:
			frappe.throw(_("Could not retrieve transaction status from Midtrans"))
		
		# Only settlement, capture, or pending can be refunded
		valid_statuses = ["settlement", "capture"]
		if status.get("transaction_status") not in valid_statuses:
			frappe.throw(
				_("Transaction status '{0}' cannot be refunded. "
				  "Only settled transactions can be refunded.").format(
					status.get("transaction_status")
				)
			)
		
		return True
	
	def process(self) -> Dict[str, Any]:
		"""Process refund with Midtrans."""
		transaction_id = self.get_midtrans_transaction_id()
		
		if not transaction_id:
			return {
				"success": False,
				"refund_id": None,
				"message": "Transaction ID not found",
				"data": {}
			}
		
		try:
			# Prepare refund request
			url = self._get_api_url(f"/v2/{transaction_id}/refund")
			headers = self._get_headers()
			
			payload = {
				"refund_key": f"refund-{self.refund_request.name}",
				"amount": int(self.refund_request.refund_amount),
				"reason": self.refund_request.reason or "Customer refund request"
			}
			
			# Send refund request
			response = requests.post(url, json=payload, headers=headers, timeout=30)
			data = response.json()
			
			# Check response
			if response.status_code == 200 and data.get("status_code") == "200":
				return {
					"success": True,
					"refund_id": data.get("refund_key") or data.get("transaction_id"),
					"message": "Refund processed successfully",
					"data": data
				}
			else:
				return {
					"success": False,
					"refund_id": None,
					"message": data.get("status_message", "Refund failed"),
					"data": data
				}
				
		except requests.RequestException as e:
			self.log_error(f"Midtrans API request failed: {str(e)}")
			return {
				"success": False,
				"refund_id": None,
				"message": f"API request failed: {str(e)}",
				"data": {}
			}
	
	def handle_webhook(self, payload: Dict[str, Any]) -> None:
		"""Handle Midtrans refund webhook."""
		transaction_status = payload.get("transaction_status")
		
		if transaction_status == "refund":
			# Find refund request by transaction ID
			transaction_id = payload.get("transaction_id")
			refund_key = payload.get("refund_key")
			
			# Update refund status
			if refund_key:
				refund_requests = frappe.get_all(
					"Refund Request",
					filters={
						"gateway_refund_id": refund_key,
						"status": ["in", ["Pending", "Processing"]]
					}
				)
				
				for rr in refund_requests:
					refund_doc = frappe.get_doc("Refund Request", rr.name)
					refund_doc.update_status(
						"Completed",
						gateway_refund_id=refund_key,
						gateway_response=payload
					)
	
	def get_midtrans_transaction_id(self) -> str:
		"""Get Midtrans transaction ID from payment data."""
		# Midtrans uses order_id as the primary identifier
		return self.payment_data.get("order_id") or self.payment_data.get("transaction_id")
	
	def get_transaction_id(self) -> str:
		"""Override to get Midtrans-specific transaction ID."""
		return self.get_midtrans_transaction_id()
	
	def _get_api_url(self, endpoint: str) -> str:
		"""Get Midtrans API URL."""
		if self.gateway_settings.sandbox_mode:
			base_url = "https://api.sandbox.midtrans.com"
		else:
			base_url = "https://api.midtrans.com"
		
		return f"{base_url}{endpoint}"
	
	def _get_headers(self) -> Dict[str, str]:
		"""Get API headers with authentication."""
		server_key = self.gateway_settings.get_password("server_key")
		auth_string = base64.b64encode(f"{server_key}:".encode()).decode()
		
		return {
			"Authorization": f"Basic {auth_string}",
			"Content-Type": "application/json",
			"Accept": "application/json"
		}
	
	def _get_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
		"""Get transaction status from Midtrans."""
		try:
			url = self._get_api_url(f"/v2/{transaction_id}/status")
			headers = self._get_headers()
			
			response = requests.get(url, headers=headers, timeout=30)
			
			if response.status_code == 200:
				return response.json()
			
			return None
			
		except requests.RequestException:
			return None
