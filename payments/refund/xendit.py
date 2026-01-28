# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""
Xendit refund handler implementation.
"""

import frappe
from frappe import _
from typing import Dict, Any
import requests
from payments.refund.base import RefundHandler


class XenditRefundHandler(RefundHandler):
	"""
	Refund handler for Xendit payment gateway.
	
	Uses Xendit API for refund processing.
	API Docs: https://developers.xendit.co/api-reference/#refunds
	"""
	
	def validate(self) -> bool:
		"""Validate Xendit refund request."""
		# Check if we have gateway settings
		if not self.gateway_settings:
			frappe.throw(_("Xendit Settings not found"))
		
		# Check if we have charge/invoice ID
		charge_id = self.get_xendit_charge_id()
		if not charge_id:
			frappe.throw(_("Xendit charge/invoice ID not found in payment data"))
		
		return True
	
	def process(self) -> Dict[str, Any]:
		"""Process refund with Xendit."""
		charge_id = self.get_xendit_charge_id()
		
		if not charge_id:
			return {
				"success": False,
				"refund_id": None,
				"message": "Charge ID not found",
				"data": {}
			}
		
		try:
			# Prepare refund request
			url = "https://api.xendit.co/refunds"
			headers = self._get_headers()
			
			payload = {
				"invoice_id": charge_id,
				"amount": int(self.refund_request.refund_amount),
				"reason": self._map_reason(self.refund_request.reason),
				"metadata": {
					"refund_request": self.refund_request.name,
					"original_reason": self.refund_request.reason
				}
			}
			
			# Send refund request
			response = requests.post(url, json=payload, headers=headers, timeout=30)
			data = response.json()
			
			# Check response
			if response.status_code in [200, 201]:
				refund_id = data.get("id")
				status = data.get("status", "").upper()
				
				# Xendit refund might be pending
				if status == "SUCCEEDED":
					return {
						"success": True,
						"refund_id": refund_id,
						"message": "Refund processed successfully",
						"data": data
					}
				elif status == "PENDING":
					return {
						"success": True,
						"refund_id": refund_id,
						"message": "Refund is pending processing",
						"data": data
					}
				else:
					return {
						"success": False,
						"refund_id": refund_id,
						"message": f"Refund status: {status}",
						"data": data
					}
			else:
				error_message = data.get("message", "Refund failed")
				return {
					"success": False,
					"refund_id": None,
					"message": error_message,
					"data": data
				}
				
		except requests.RequestException as e:
			self.log_error(f"Xendit API request failed: {str(e)}")
			return {
				"success": False,
				"refund_id": None,
				"message": f"API request failed: {str(e)}",
				"data": {}
			}
	
	def handle_webhook(self, payload: Dict[str, Any]) -> None:
		"""Handle Xendit refund webhook."""
		event = payload.get("event")
		
		if event in ["refund.succeeded", "refund.failed"]:
			refund_data = payload.get("data", {})
			refund_id = refund_data.get("id")
			
			# Find refund request by gateway refund ID
			refund_requests = frappe.get_all(
				"Refund Request",
				filters={
					"gateway_refund_id": refund_id,
					"status": ["in", ["Pending", "Processing"]]
				}
			)
			
			for rr in refund_requests:
				refund_doc = frappe.get_doc("Refund Request", rr.name)
				
				if event == "refund.succeeded":
					refund_doc.update_status(
						"Completed",
						gateway_refund_id=refund_id,
						gateway_response=payload
					)
				else:
					failure_reason = refund_data.get("failure_reason", "Refund failed")
					refund_doc.update_status(
						"Failed",
						gateway_refund_id=refund_id,
						gateway_response=payload,
						error_message=failure_reason
					)
	
	def get_xendit_charge_id(self) -> str:
		"""Get Xendit charge/invoice ID from payment data."""
		# Xendit uses different IDs depending on payment type
		return (
			self.payment_data.get("xendit_invoice_id") or
			self.payment_data.get("invoice_id") or
			self.payment_data.get("charge_id") or
			self.payment_data.get("external_id")
		)
	
	def get_transaction_id(self) -> str:
		"""Override to get Xendit-specific transaction ID."""
		return self.get_xendit_charge_id()
	
	def _get_headers(self) -> Dict[str, str]:
		"""Get API headers with authentication."""
		api_key = self.gateway_settings.get_password("api_key")
		
		return {
			"Authorization": f"Basic {self._encode_api_key(api_key)}",
			"Content-Type": "application/json"
		}
	
	def _encode_api_key(self, api_key: str) -> str:
		"""Encode API key for Basic auth."""
		import base64
		return base64.b64encode(f"{api_key}:".encode()).decode()
	
	def _map_reason(self, reason: str) -> str:
		"""Map reason to Xendit's allowed values."""
		# Xendit has specific reason values
		reason_lower = (reason or "").lower()
		
		if "duplicate" in reason_lower:
			return "DUPLICATE"
		elif "fraud" in reason_lower:
			return "FRAUDULENT"
		elif "request" in reason_lower or "customer" in reason_lower:
			return "REQUESTED_BY_CUSTOMER"
		else:
			return "OTHERS"
