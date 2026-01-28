# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""
Refund API endpoints.
"""

import frappe
from frappe import _
from frappe.utils import flt
import json


@frappe.whitelist()
def initiate_refund(integration_request: str, amount: float, reason: str) -> dict:
	"""
	Initiate a refund request.
	
	Args:
		integration_request: Name of the Integration Request to refund
		amount: Amount to refund
		reason: Reason for refund
		
	Returns:
		Dictionary with refund request details
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"))
	
	# Validate inputs
	if not integration_request:
		frappe.throw(_("Integration Request is required"))
	
	if not amount or flt(amount) <= 0:
		frappe.throw(_("Valid refund amount is required"))
	
	if not reason:
		frappe.throw(_("Refund reason is required"))
	
	# Check permission
	if not frappe.has_permission("Integration Request", "read", integration_request):
		frappe.throw(_("You do not have permission to refund this payment"))
	
	# Create refund request
	refund_request = frappe.get_doc({
		"doctype": "Refund Request",
		"integration_request": integration_request,
		"refund_amount": flt(amount),
		"reason": reason,
		"status": "Draft"
	})
	
	refund_request.insert()
	
	return {
		"success": True,
		"refund_request": refund_request.name,
		"message": _("Refund request created. Submit to process.")
	}


@frappe.whitelist()
def get_refund_status(refund_request: str) -> dict:
	"""
	Get status of a refund request.
	
	Args:
		refund_request: Name of the Refund Request
		
	Returns:
		Dictionary with refund status details
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"))
	
	if not frappe.has_permission("Refund Request", "read", refund_request):
		frappe.throw(_("You do not have permission to view this refund"))
	
	doc = frappe.get_doc("Refund Request", refund_request)
	
	return {
		"name": doc.name,
		"status": doc.status,
		"refund_amount": doc.refund_amount,
		"refund_type": doc.refund_type,
		"gateway_refund_id": doc.gateway_refund_id,
		"processed_at": doc.processed_at,
		"error_message": doc.error_message
	}


@frappe.whitelist()
def get_refundable_amount(integration_request: str) -> dict:
	"""
	Get the maximum amount that can be refunded for a payment.
	
	Args:
		integration_request: Name of the Integration Request
		
	Returns:
		Dictionary with refundable amount details
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"))
	
	ir = frappe.get_doc("Integration Request", integration_request)
	
	# Get original amount
	try:
		data = json.loads(ir.data or "{}")
		original_amount = flt(data.get("amount", 0))
	except (json.JSONDecodeError, TypeError):
		original_amount = 0
	
	# Get already refunded amount
	existing_refunds = frappe.get_all(
		"Refund Request",
		filters={
			"integration_request": integration_request,
			"status": ["in", ["Completed", "Processing", "Pending"]]
		},
		fields=["sum(refund_amount) as total_refunded"]
	)
	
	total_refunded = flt(existing_refunds[0].total_refunded) if existing_refunds else 0
	refundable = original_amount - total_refunded
	
	return {
		"original_amount": original_amount,
		"total_refunded": total_refunded,
		"refundable_amount": max(0, refundable),
		"currency": data.get("currency", "IDR") if 'data' in dir() else "IDR"
	}


@frappe.whitelist()
def get_refund_history(integration_request: str) -> list:
	"""
	Get refund history for a payment.
	
	Args:
		integration_request: Name of the Integration Request
		
	Returns:
		List of refund requests
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"))
	
	refunds = frappe.get_all(
		"Refund Request",
		filters={"integration_request": integration_request},
		fields=[
			"name", "status", "refund_amount", "refund_type",
			"reason", "gateway_refund_id", "processed_at", "creation"
		],
		order_by="creation desc"
	)
	
	return refunds


@frappe.whitelist(allow_guest=True)
def refund_webhook(gateway: str):
	"""
	Handle refund webhooks from payment gateways.
	
	Args:
		gateway: Payment gateway name (midtrans, xendit, razorpay, etc.)
	"""
	from payments.refund.processor import get_refund_handler
	from payments.refund.base import GenericRefundHandler
	
	try:
		payload = frappe.request.get_json()
		
		if not payload:
			frappe.local.response.http_status_code = 400
			return {"error": "No payload received"}
		
		# Log webhook for debugging
		frappe.log_error(
			f"Refund webhook from {gateway}:\n{json.dumps(payload, indent=2)}",
			"Refund Webhook"
		)
		
		# Route to appropriate handler
		handler_map = {
			"midtrans": "payments.refund.midtrans.MidtransRefundHandler",
			"xendit": "payments.refund.xendit.XenditRefundHandler",
			"razorpay": "payments.refund.razorpay.RazorpayRefundHandler",
			"stripe": "payments.refund.stripe.StripeRefundHandler",
			"paypal": "payments.refund.paypal.PayPalRefundHandler",
		}
		
		handler_path = handler_map.get(gateway.lower())
		
		if handler_path:
			try:
				module_path, class_name = handler_path.rsplit(".", 1)
				module = frappe.get_module(module_path)
				handler_class = getattr(module, class_name)
				
				# Create a temporary handler to process webhook
				# Note: We need a refund request name, but for webhook we don't have it
				# So we call handle_webhook as a class method pattern
				handler_class.handle_webhook(None, payload)
				
			except Exception as e:
				frappe.log_error(
					f"Error handling {gateway} refund webhook: {str(e)}",
					"Refund Webhook Error"
				)
		
		return {"success": True}
		
	except Exception as e:
		frappe.log_error(
			f"Refund webhook error: {str(e)}",
			"Refund Webhook Error"
		)
		frappe.local.response.http_status_code = 500
		return {"error": str(e)}
