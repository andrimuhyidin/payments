# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""
Stripe refund handler implementation.
"""

import frappe
from frappe import _
from typing import Dict, Any
from payments.refund.base import RefundHandler


class StripeRefundHandler(RefundHandler):
	"""
	Refund handler for Stripe payment gateway.
	
	Uses Stripe Python SDK for refund processing.
	API Docs: https://stripe.com/docs/api/refunds
	"""
	
	def validate(self) -> bool:
		"""Validate Stripe refund request."""
		if not self.gateway_settings:
			frappe.throw(_("Stripe Settings not found"))
		
		payment_intent_id = self.get_stripe_payment_id()
		if not payment_intent_id:
			frappe.throw(_("Stripe payment intent ID not found in payment data"))
		
		return True
	
	def process(self) -> Dict[str, Any]:
		"""Process refund with Stripe."""
		try:
			import stripe
		except ImportError:
			return {
				"success": False,
				"refund_id": None,
				"message": "Stripe library not installed",
				"data": {}
			}
		
		payment_intent_id = self.get_stripe_payment_id()
		
		if not payment_intent_id:
			return {
				"success": False,
				"refund_id": None,
				"message": "Payment Intent ID not found",
				"data": {}
			}
		
		try:
			# Configure Stripe
			stripe.api_key = self.gateway_settings.get_password("secret_key")
			
			# Amount in smallest currency unit (cents)
			amount_in_cents = int(self.refund_request.refund_amount * 100)
			
			# Create refund
			refund = stripe.Refund.create(
				payment_intent=payment_intent_id,
				amount=amount_in_cents,
				reason="requested_by_customer",
				metadata={
					"refund_request": self.refund_request.name,
					"reason": self.refund_request.reason
				}
			)
			
			if refund.status == "succeeded":
				return {
					"success": True,
					"refund_id": refund.id,
					"message": "Refund processed successfully",
					"data": dict(refund)
				}
			elif refund.status == "pending":
				return {
					"success": True,
					"refund_id": refund.id,
					"message": "Refund is pending",
					"data": dict(refund)
				}
			else:
				return {
					"success": False,
					"refund_id": refund.id,
					"message": f"Refund status: {refund.status}",
					"data": dict(refund)
				}
				
		except stripe.error.StripeError as e:
			self.log_error(f"Stripe refund error: {str(e)}")
			return {
				"success": False,
				"refund_id": None,
				"message": str(e),
				"data": {}
			}
		except Exception as e:
			self.log_error(f"Stripe refund error: {str(e)}")
			return {
				"success": False,
				"refund_id": None,
				"message": str(e),
				"data": {}
			}
	
	def handle_webhook(self, payload: Dict[str, Any]) -> None:
		"""Handle Stripe refund webhook."""
		event_type = payload.get("type")
		
		if event_type in ["charge.refunded", "refund.created", "refund.updated"]:
			refund_data = payload.get("data", {}).get("object", {})
			refund_id = refund_data.get("id")
			
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
				status = refund_data.get("status")
				
				if status == "succeeded":
					refund_doc.update_status(
						"Completed",
						gateway_refund_id=refund_id,
						gateway_response=payload
					)
				elif status == "failed":
					refund_doc.update_status(
						"Failed",
						gateway_refund_id=refund_id,
						gateway_response=payload,
						error_message=refund_data.get("failure_reason", "Refund failed")
					)
	
	def get_stripe_payment_id(self) -> str:
		"""Get Stripe payment intent ID from payment data."""
		return (
			self.payment_data.get("payment_intent") or
			self.payment_data.get("stripe_payment_intent_id") or
			self.payment_data.get("charge_id")
		)
	
	def get_transaction_id(self) -> str:
		"""Override to get Stripe-specific payment ID."""
		return self.get_stripe_payment_id()
