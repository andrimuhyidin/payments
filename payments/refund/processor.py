# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""
Refund processor module.

Handles refund processing orchestration and gateway handler selection.
"""

import frappe
from frappe import _
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from typing import Optional, Type
from payments.refund.base import RefundHandler, GenericRefundHandler


# Registry of gateway-specific refund handlers
REFUND_HANDLERS = {
	"Midtrans": "payments.refund.midtrans.MidtransRefundHandler",
	"Xendit": "payments.refund.xendit.XenditRefundHandler",
	"Razorpay": "payments.refund.razorpay.RazorpayRefundHandler",
	"Stripe": "payments.refund.stripe.StripeRefundHandler",
	"PayPal": "payments.refund.paypal.PayPalRefundHandler",
}


def get_refund_handler(refund_request_name: str) -> RefundHandler:
	"""
	Get appropriate refund handler for a refund request.
	
	Args:
		refund_request_name: Name of the Refund Request document
		
	Returns:
		RefundHandler instance for the payment gateway
	"""
	refund_request = frappe.get_doc("Refund Request", refund_request_name)
	gateway = refund_request.payment_gateway
	
	if gateway and gateway in REFUND_HANDLERS:
		handler_path = REFUND_HANDLERS[gateway]
		try:
			module_path, class_name = handler_path.rsplit(".", 1)
			module = frappe.get_module(module_path)
			handler_class = getattr(module, class_name)
			return handler_class(refund_request_name)
		except (ImportError, AttributeError) as e:
			frappe.log_error(
				f"Failed to load refund handler for {gateway}: {str(e)}",
				"Refund Handler Error"
			)
	
	# Return generic handler if no specific handler found
	return GenericRefundHandler(refund_request_name)


def process_refund(refund_request: str):
	"""
	Process a refund request.
	
	This function is called asynchronously via frappe.enqueue().
	
	Args:
		refund_request: Name of the Refund Request document
	"""
	try:
		# Get handler for this refund
		handler = get_refund_handler(refund_request)
		
		# Update status to Processing
		handler.update_refund_status("Processing")
		
		# Validate refund
		if not handler.validate():
			handler.update_refund_status(
				"Failed",
				error="Validation failed"
			)
			return
		
		# Process refund with gateway
		result = handler.process()
		
		if result.get("success"):
			handler.update_refund_status(
				"Completed",
				refund_id=result.get("refund_id"),
				response=result.get("data")
			)
			
			# Create refund payment entry if applicable
			create_refund_payment_entry(refund_request)
			
		else:
			# Check if manual processing is required
			if result.get("data", {}).get("manual_processing"):
				handler.update_refund_status(
					"Pending",
					response=result.get("data"),
					error=result.get("message")
				)
			else:
				handler.update_refund_status(
					"Failed",
					response=result.get("data"),
					error=result.get("message")
				)
				
	except Exception as e:
		frappe.log_error(
			f"Refund processing error for {refund_request}: {str(e)}",
			"Refund Processing Error"
		)
		
		# Update status to failed
		try:
			refund_doc = frappe.get_doc("Refund Request", refund_request)
			refund_doc.update_status("Failed", error_message=str(e))
		except Exception:
			pass


def create_refund_payment_entry(refund_request: str):
	"""
	Create a Payment Entry for the refund if ERPNext is installed.
	
	Args:
		refund_request: Name of the Refund Request document
	"""
	if "erpnext" not in frappe.get_installed_apps():
		return
	
	try:
		refund_doc = frappe.get_doc("Refund Request", refund_request)
		ir = frappe.get_doc("Integration Request", refund_doc.integration_request)
		
		# Get original payment entry if exists
		import json
		data = json.loads(ir.data or "{}")
		
		reference_doctype = data.get("reference_doctype")
		reference_docname = data.get("reference_docname")
		
		if not reference_doctype or not reference_docname:
			return
		
		# Check if we can create payment entry
		if reference_doctype not in ["Sales Invoice", "Sales Order"]:
			return
		
		# Create refund payment entry
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
		
		pe = get_payment_entry(reference_doctype, reference_docname)
		pe.payment_type = "Pay"  # Refund is outgoing payment
		pe.paid_amount = refund_doc.refund_amount
		pe.reference_no = refund_doc.gateway_refund_id or refund_doc.name
		pe.reference_date = frappe.utils.today()
		pe.remarks = f"Refund for {reference_docname} - {refund_doc.reason}"
		
		pe.insert(ignore_permissions=True)
		pe.submit()
		
		frappe.msgprint(
			_("Payment Entry {0} created for refund").format(pe.name),
			indicator="green"
		)
		
	except Exception as e:
		frappe.log_error(
			f"Failed to create refund payment entry: {str(e)}",
			"Refund Payment Entry Error"
		)
