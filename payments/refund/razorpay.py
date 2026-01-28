# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""
Razorpay refund handler implementation.
"""

import frappe
from frappe import _
from typing import Dict, Any
import requests
from payments.refund.base import RefundHandler


class RazorpayRefundHandler(RefundHandler):
	"""
	Refund handler for Razorpay payment gateway.
	
	Uses Razorpay API for refund processing.
	API Docs: https://razorpay.com/docs/api/refunds/
	"""
	
	def validate(self) -> bool:
		"""Validate Razorpay refund request."""
		if not self.gateway_settings:
			frappe.throw(_("Razorpay Settings not found"))
		
		payment_id = self.get_razorpay_payment_id()
		if not payment_id:
			frappe.throw(_("Razorpay payment ID not found in payment data"))
		
		return True
	
	def process(self) -> Dict[str, Any]:
		"""Process refund with Razorpay."""
		payment_id = self.get_razorpay_payment_id()
		
		if not payment_id:
			return {
				"success": False,
				"refund_id": None,
				"message": "Payment ID not found",
				"data": {}
			}
		
		try:
			# Prepare refund request
			url = f"https://api.razorpay.com/v1/payments/{payment_id}/refund"
			auth = self._get_auth()
			
			# Amount should be in paise (smallest currency unit)
			amount_in_paise = int(self.refund_request.refund_amount * 100)
			
			payload = {
				"amount": amount_in_paise,
				"notes": {
					"refund_request": self.refund_request.name,
					"reason": self.refund_request.reason
				}
			}
			
			# Send refund request
			response = requests.post(url, json=payload, auth=auth, timeout=30)
			data = response.json()
			
			# Check response
			if response.status_code == 200:
				refund_id = data.get("id")
				status = data.get("status")
				
				if status == "processed":
					return {
						"success": True,
						"refund_id": refund_id,
						"message": "Refund processed successfully",
						"data": data
					}
				elif status == "pending":
					return {
						"success": True,
						"refund_id": refund_id,
						"message": "Refund is pending",
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
				error = data.get("error", {})
				error_message = error.get("description", "Refund failed")
				return {
					"success": False,
					"refund_id": None,
					"message": error_message,
					"data": data
				}
				
		except requests.RequestException as e:
			self.log_error(f"Razorpay API request failed: {str(e)}")
			return {
				"success": False,
				"refund_id": None,
				"message": f"API request failed: {str(e)}",
				"data": {}
			}
	
	def handle_webhook(self, payload: Dict[str, Any]) -> None:
		"""Handle Razorpay refund webhook."""
		event = payload.get("event")
		
		if event in ["refund.processed", "refund.failed"]:
			refund_entity = payload.get("payload", {}).get("refund", {}).get("entity", {})
			refund_id = refund_entity.get("id")
			
			# Find refund request
			refund_requests = frappe.get_all(
				"Refund Request",
				filters={
					"gateway_refund_id": refund_id,
					"status": ["in", ["Pending", "Processing"]]
				}
			)
			
			for rr in refund_requests:
				refund_doc = frappe.get_doc("Refund Request", rr.name)
				
				if event == "refund.processed":
					refund_doc.update_status(
						"Completed",
						gateway_refund_id=refund_id,
						gateway_response=payload
					)
				else:
					refund_doc.update_status(
						"Failed",
						gateway_refund_id=refund_id,
						gateway_response=payload,
						error_message="Refund failed"
					)
	
	def get_razorpay_payment_id(self) -> str:
		"""Get Razorpay payment ID from payment data."""
		return (
			self.payment_data.get("razorpay_payment_id") or
			self.payment_data.get("payment_id")
		)
	
	def get_transaction_id(self) -> str:
		"""Override to get Razorpay-specific payment ID."""
		return self.get_razorpay_payment_id()
	
	def _get_auth(self):
		"""Get authentication tuple for requests."""
		key_id = self.gateway_settings.api_key
		key_secret = self.gateway_settings.get_password("api_secret")
		return (key_id, key_secret)
