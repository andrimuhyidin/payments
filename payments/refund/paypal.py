# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""
PayPal refund handler implementation.
"""

import frappe
from frappe import _
from typing import Dict, Any
import requests
from payments.refund.base import RefundHandler


class PayPalRefundHandler(RefundHandler):
	"""
	Refund handler for PayPal payment gateway.
	
	Uses PayPal REST API for refund processing.
	API Docs: https://developer.paypal.com/docs/api/payments/v2/
	"""
	
	def validate(self) -> bool:
		"""Validate PayPal refund request."""
		if not self.gateway_settings:
			frappe.throw(_("PayPal Settings not found"))
		
		capture_id = self.get_paypal_capture_id()
		if not capture_id:
			frappe.throw(_("PayPal capture ID not found in payment data"))
		
		return True
	
	def process(self) -> Dict[str, Any]:
		"""Process refund with PayPal."""
		capture_id = self.get_paypal_capture_id()
		
		if not capture_id:
			return {
				"success": False,
				"refund_id": None,
				"message": "Capture ID not found",
				"data": {}
			}
		
		try:
			# Get access token
			access_token = self._get_access_token()
			
			if not access_token:
				return {
					"success": False,
					"refund_id": None,
					"message": "Failed to get PayPal access token",
					"data": {}
				}
			
			# Prepare refund request
			url = self._get_api_url(f"/v2/payments/captures/{capture_id}/refund")
			headers = {
				"Authorization": f"Bearer {access_token}",
				"Content-Type": "application/json"
			}
			
			payload = {
				"amount": {
					"value": str(self.refund_request.refund_amount),
					"currency_code": self.refund_request.original_currency or "USD"
				},
				"note_to_payer": self.refund_request.reason or "Refund"
			}
			
			# Send refund request
			response = requests.post(url, json=payload, headers=headers, timeout=30)
			data = response.json()
			
			# Check response
			if response.status_code in [200, 201]:
				refund_id = data.get("id")
				status = data.get("status", "").upper()
				
				if status == "COMPLETED":
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
				error_details = data.get("details", [{}])
				error_message = error_details[0].get("description") if error_details else "Refund failed"
				return {
					"success": False,
					"refund_id": None,
					"message": error_message,
					"data": data
				}
				
		except requests.RequestException as e:
			self.log_error(f"PayPal API request failed: {str(e)}")
			return {
				"success": False,
				"refund_id": None,
				"message": f"API request failed: {str(e)}",
				"data": {}
			}
	
	def handle_webhook(self, payload: Dict[str, Any]) -> None:
		"""Handle PayPal refund webhook."""
		event_type = payload.get("event_type")
		
		if event_type in ["PAYMENT.CAPTURE.REFUNDED"]:
			resource = payload.get("resource", {})
			refund_id = resource.get("id")
			
			if not refund_id:
				return
			
			refund_requests = frappe.get_all(
				"Refund Request",
				filters={
					"gateway_refund_id": refund_id,
					"status": ["in", ["Pending", "Processing"]]
				}
			)
			
			for rr in refund_requests:
				refund_doc = frappe.get_doc("Refund Request", rr.name)
				status = resource.get("status", "").upper()
				
				if status == "COMPLETED":
					refund_doc.update_status(
						"Completed",
						gateway_refund_id=refund_id,
						gateway_response=payload
					)
				elif status == "FAILED":
					refund_doc.update_status(
						"Failed",
						gateway_refund_id=refund_id,
						gateway_response=payload,
						error_message="Refund failed"
					)
	
	def get_paypal_capture_id(self) -> str:
		"""Get PayPal capture ID from payment data."""
		return (
			self.payment_data.get("capture_id") or
			self.payment_data.get("paypal_capture_id") or
			self.payment_data.get("transaction_id")
		)
	
	def get_transaction_id(self) -> str:
		"""Override to get PayPal-specific capture ID."""
		return self.get_paypal_capture_id()
	
	def _get_api_url(self, endpoint: str) -> str:
		"""Get PayPal API URL."""
		if self.gateway_settings.sandbox:
			base_url = "https://api-m.sandbox.paypal.com"
		else:
			base_url = "https://api-m.paypal.com"
		
		return f"{base_url}{endpoint}"
	
	def _get_access_token(self) -> str:
		"""Get PayPal OAuth access token."""
		try:
			client_id = self.gateway_settings.client_id
			client_secret = self.gateway_settings.get_password("client_secret")
			
			url = self._get_api_url("/v1/oauth2/token")
			
			response = requests.post(
				url,
				data={"grant_type": "client_credentials"},
				auth=(client_id, client_secret),
				timeout=30
			)
			
			if response.status_code == 200:
				return response.json().get("access_token")
			
			return None
			
		except Exception as e:
			self.log_error(f"Failed to get PayPal access token: {str(e)}")
			return None
