# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

"""
Webhook handlers and payment finalization for Indonesian Payment Gateways.
Handles callbacks from Midtrans and Xendit.
"""

from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.utils import nowdate

from payments.payment_gateways.midtrans.constants import (
	FAILED_STATUSES as MIDTRANS_FAILED_STATUSES,
)
from payments.payment_gateways.midtrans.constants import (
	SUCCESSFUL_STATUSES as MIDTRANS_SUCCESSFUL_STATUSES,
)
from payments.payment_gateways.midtrans.signature_validator import MidtransSignatureValidator
from payments.payment_gateways.xendit.callback_validator import XenditCallbackValidator
from payments.payment_gateways.xendit.constants import (
	FAILED_STATUSES as XENDIT_FAILED_STATUSES,
)
from payments.payment_gateways.xendit.constants import (
	SUCCESSFUL_STATUSES as XENDIT_SUCCESSFUL_STATUSES,
)


@frappe.whitelist(allow_guest=True)
def midtrans_callback(**kwargs):
	"""
	Handle Midtrans webhook/notification callback.

	Midtrans sends HTTP POST notifications for transaction status changes.
	This endpoint validates the signature and processes the payment accordingly.
	"""
	try:
		# Get JSON data from request
		data = frappe.request.get_json() if frappe.request else kwargs

		if not data:
			frappe.throw(_("No data received"))

		# Extract required fields for signature validation
		order_id = data.get("order_id")
		status_code = str(data.get("status_code", ""))
		gross_amount = str(data.get("gross_amount", ""))
		signature_key = data.get("signature_key")
		transaction_status = data.get("transaction_status", "").lower()
		fraud_status = data.get("fraud_status", "").lower()

		if not all([order_id, status_code, gross_amount, signature_key]):
			frappe.throw(_("Missing required fields in callback data"))

		# Get Midtrans settings and server key
		settings = frappe.get_doc("Midtrans Settings")
		server_key = settings.get_password("server_key")

		# Validate signature
		validator = MidtransSignatureValidator(
			order_id=order_id,
			status_code=status_code,
			gross_amount=gross_amount,
			server_key=server_key,
			signature_key=signature_key,
		)
		validator.validate()

		# Find Integration Request by order_id
		integration_request_doc = get_integration_request_by_order_id(
			order_id=order_id,
			service_name="Midtrans",
			field_name="midtrans_order_id",
		)

		if not integration_request_doc:
			frappe.throw(_("No Integration Request found for order: {0}").format(order_id))

		integration_request_dict = frappe.parse_json(integration_request_doc.data)

		# Update with Midtrans response data
		integration_request_dict.update({
			"midtrans_transaction_id": data.get("transaction_id"),
			"midtrans_transaction_status": transaction_status,
			"midtrans_fraud_status": fraud_status,
			"midtrans_payment_type": data.get("payment_type"),
			"midtrans_status_code": status_code,
		})

		# Check transaction status
		# For credit card: capture with fraud_status=accept is success
		# For other payment types: settlement is success
		is_successful = (
			transaction_status in MIDTRANS_SUCCESSFUL_STATUSES
			and fraud_status != "deny"
		)

		if is_successful:
			integration_request_doc.status = "Completed"
			integration_request_doc.data = frappe.as_json(integration_request_dict)
			integration_request_doc.save(ignore_permissions=True)
			frappe.db.commit()

			# Finalize payment
			return handle_payment_success(integration_request_dict, gateway="Midtrans")

		elif transaction_status in MIDTRANS_FAILED_STATUSES:
			integration_request_doc.status = "Failed"
			integration_request_doc.error = f"Transaction {transaction_status}: {data.get('status_message', '')}"
			integration_request_doc.data = frappe.as_json(integration_request_dict)
			integration_request_doc.save(ignore_permissions=True)
			frappe.db.commit()

			frappe.log_error(
				message=f"Midtrans payment failed: {transaction_status}",
				title="Midtrans Payment Failed",
			)
			return {"status": "Failed", "message": f"Payment {transaction_status}"}

		else:
			# Pending or other status
			integration_request_doc.data = frappe.as_json(integration_request_dict)
			integration_request_doc.save(ignore_permissions=True)
			frappe.db.commit()

			return {"status": "Pending", "message": f"Payment status: {transaction_status}"}

	except frappe.PermissionError:
		frappe.local.response["http_status_code"] = 403
		return {"status": "Error", "message": "Invalid signature"}
	except Exception:
		frappe.log_error(
			message=frappe.get_traceback(),
			title="Midtrans Callback Error",
		)
		frappe.local.response["http_status_code"] = 500
		return {"status": "Error", "message": "Internal server error"}


@frappe.whitelist(allow_guest=True)
def xendit_callback(**kwargs):
	"""
	Handle Xendit webhook callback.

	Xendit sends HTTP POST callbacks when invoice status changes.
	This endpoint validates the callback token and processes the payment accordingly.
	"""
	try:
		# Get callback token from header
		incoming_token = frappe.request.headers.get("x-callback-token", "")

		# Get Xendit settings and callback token
		settings = frappe.get_doc("Xendit Settings")
		callback_token = settings.get_password("callback_token")

		# Validate callback token
		validator = XenditCallbackValidator(
			callback_token=callback_token,
			incoming_token=incoming_token,
		)
		validator.validate()

		# Get JSON data from request
		data = frappe.request.get_json() if frappe.request else kwargs

		if not data:
			frappe.throw(_("No data received"))

		# Extract required fields
		external_id = data.get("external_id")
		xendit_invoice_id = data.get("id")
		status = data.get("status", "").upper()

		if not external_id:
			frappe.throw(_("Missing external_id in callback data"))

		# Find Integration Request by external_id
		integration_request_doc = get_integration_request_by_order_id(
			order_id=external_id,
			service_name="Xendit",
			field_name="xendit_external_id",
		)

		if not integration_request_doc:
			frappe.throw(_("No Integration Request found for external_id: {0}").format(external_id))

		integration_request_dict = frappe.parse_json(integration_request_doc.data)

		# Update with Xendit response data
		integration_request_dict.update({
			"xendit_invoice_id": xendit_invoice_id,
			"xendit_status": status,
			"xendit_payment_method": data.get("payment_method"),
			"xendit_payment_channel": data.get("payment_channel"),
			"xendit_paid_amount": data.get("paid_amount"),
			"xendit_paid_at": data.get("paid_at"),
		})

		# Check payment status
		if status in XENDIT_SUCCESSFUL_STATUSES:
			integration_request_doc.status = "Completed"
			integration_request_doc.data = frappe.as_json(integration_request_dict)
			integration_request_doc.save(ignore_permissions=True)
			frappe.db.commit()

			# Finalize payment
			return handle_payment_success(integration_request_dict, gateway="Xendit")

		elif status in XENDIT_FAILED_STATUSES:
			integration_request_doc.status = "Failed"
			integration_request_doc.error = f"Invoice {status}"
			integration_request_doc.data = frappe.as_json(integration_request_dict)
			integration_request_doc.save(ignore_permissions=True)
			frappe.db.commit()

			frappe.log_error(
				message=f"Xendit payment failed: {status}",
				title="Xendit Payment Failed",
			)
			return {"status": "Failed", "message": f"Invoice {status}"}

		else:
			# Pending or other status
			integration_request_doc.data = frappe.as_json(integration_request_dict)
			integration_request_doc.save(ignore_permissions=True)
			frappe.db.commit()

			return {"status": "Pending", "message": f"Invoice status: {status}"}

	except frappe.PermissionError:
		frappe.local.response["http_status_code"] = 403
		return {"status": "Error", "message": "Invalid callback token"}
	except Exception:
		frappe.log_error(
			message=frappe.get_traceback(),
			title="Xendit Callback Error",
		)
		frappe.local.response["http_status_code"] = 500
		return {"status": "Error", "message": "Internal server error"}


def get_integration_request_by_order_id(
	order_id: str,
	service_name: str,
	field_name: str,
) -> "frappe.Document | None":
	"""
	Fetch Integration Request linked to a payment gateway order.

	Args:
	    order_id: The order/external ID to search for
	    service_name: The integration service name (Midtrans/Xendit)
	    field_name: The JSON field name to search in data

	Returns:
	    Integration Request document or None
	"""
	integration_requests = frappe.get_all(
		"Integration Request",
		filters={
			"integration_request_service": service_name,
			"data": ["like", f'%"{field_name}": "{order_id}"%'],
		},
		fields=["name", "data", "reference_doctype", "reference_docname"],
		order_by="creation desc",
		limit=1,
	)

	if not integration_requests:
		return None

	return frappe.get_doc("Integration Request", integration_requests[0].name)


def handle_payment_success(integration_request_dict: dict, gateway: str) -> dict:
	"""
	Handle successful payment by finalizing and creating Payment Entry.

	Args:
	    integration_request_dict: Integration request data dictionary
	    gateway: Payment gateway name (Midtrans/Xendit)

	Returns:
	    dict with redirect_to and status
	"""
	redirect_to = integration_request_dict.get("redirect_to")
	reference_doctype = integration_request_dict.get("reference_doctype")
	reference_docname = integration_request_dict.get("reference_docname")

	if reference_doctype and reference_docname:
		try:
			# Try to finalize payment (create Payment Entry)
			finalize_payment(integration_request_dict, gateway=gateway)

			# Call on_payment_authorized hook
			custom_redirect_to = frappe.get_doc(
				reference_doctype, reference_docname
			).run_method("on_payment_authorized", "Completed")

			if custom_redirect_to:
				redirect_to = custom_redirect_to

		except Exception:
			frappe.log_error(
				message=frappe.get_traceback(),
				title=f"{gateway} Payment Finalization Error",
			)

	# Build redirect URL
	redirect_url = f"payment-success?doctype={reference_doctype}&docname={reference_docname}"

	if redirect_to:
		redirect_url += "&" + urlencode({"redirect_to": redirect_to})

	return {"redirect_to": redirect_url, "status": "Completed"}


def finalize_payment(integration_request_dict: dict, gateway: str) -> None:
	"""
	Finalize payment by creating Payment Entry in ERPNext.

	This function:
	1. Parses the order reference to get DocType and DocName
	2. Finds the corresponding Payment Request
	3. Creates and submits a Payment Entry

	Args:
	    integration_request_dict: Integration request data dictionary
	    gateway: Payment gateway name (Midtrans/Xendit)
	"""
	reference_doctype = integration_request_dict.get("reference_doctype")
	reference_docname = integration_request_dict.get("reference_docname")

	if not reference_doctype or not reference_docname:
		frappe.log_error(
			message="Missing reference_doctype or reference_docname in integration request",
			title=f"{gateway} Finalize Payment Error",
		)
		return

	# Get order reference for Payment Entry
	if gateway == "Midtrans":
		order_ref = integration_request_dict.get("midtrans_order_id", "")
		transaction_id = integration_request_dict.get("midtrans_transaction_id", "")
	else:  # Xendit
		order_ref = integration_request_dict.get("xendit_external_id", "")
		transaction_id = integration_request_dict.get("xendit_invoice_id", "")

	# Try to find Payment Request
	payment_request = None
	try:
		payment_requests = frappe.get_all(
			"Payment Request",
			filters={
				"reference_doctype": reference_doctype,
				"reference_name": reference_docname,
				"status": ["in", ["Initiated", "Requested"]],
			},
			fields=["name"],
			limit=1,
		)

		if payment_requests:
			payment_request = frappe.get_doc("Payment Request", payment_requests[0].name)
	except Exception:
		frappe.log_error(
			message=frappe.get_traceback(),
			title=f"{gateway} Find Payment Request Error",
		)

	if payment_request:
		try:
			# Check if erpnext is installed for Payment Entry creation
			if "erpnext" in frappe.get_installed_apps():
				from erpnext.accounts.doctype.payment_request.payment_request import (
					make_payment_entry,
				)

				# Create Payment Entry from Payment Request
				pe = make_payment_entry(payment_request.name)
				pe.reference_no = transaction_id or order_ref
				pe.reference_date = nowdate()
				pe.remarks = f"Payment via {gateway}. Order: {order_ref}"
				pe.save(ignore_permissions=True)
				pe.submit()

				# Update Payment Request status
				payment_request.status = "Paid"
				payment_request.save(ignore_permissions=True)

				frappe.db.commit()

				frappe.log_error(
					message=f"Payment Entry {pe.name} created for {reference_docname}",
					title=f"{gateway} Payment Success",
				)
			else:
				# Without ERPNext, just update Payment Request status
				payment_request.status = "Paid"
				payment_request.save(ignore_permissions=True)
				frappe.db.commit()

		except Exception:
			frappe.log_error(
				message=frappe.get_traceback(),
				title=f"{gateway} Create Payment Entry Error",
			)
	else:
		# No Payment Request found, try to update the reference document directly
		try:
			doc = frappe.get_doc(reference_doctype, reference_docname)
			if hasattr(doc, "status") and doc.status in ["Unpaid", "Pending"]:
				doc.status = "Paid"
				doc.save(ignore_permissions=True)
				frappe.db.commit()
		except Exception:
			frappe.log_error(
				message=frappe.get_traceback(),
				title=f"{gateway} Update Reference Doc Error",
			)


@frappe.whitelist(allow_guest=True)
def get_payment_status(gateway: str, order_id: str) -> dict:
	"""
	Get payment status for a given order.

	Args:
	    gateway: Payment gateway name (Midtrans/Xendit)
	    order_id: Order ID to check

	Returns:
	    dict with payment status information
	"""
	try:
		if gateway == "Midtrans":
			settings = frappe.get_doc("Midtrans Settings")
			server_key = settings.get_password("server_key")

			from payments.payment_gateways.midtrans.snap_api import MidtransSnapAPI

			api = MidtransSnapAPI(server_key=server_key, is_sandbox=bool(settings.is_sandbox))
			return api.get_transaction_status(order_id)

		elif gateway == "Xendit":
			settings = frappe.get_doc("Xendit Settings")
			secret_key = settings.get_password("secret_key")

			from payments.payment_gateways.xendit.invoice_api import XenditInvoiceAPI

			api = XenditInvoiceAPI(secret_key=secret_key)
			return api.get_invoice(order_id)

		else:
			frappe.throw(_("Unknown payment gateway: {0}").format(gateway))

	except Exception:
		frappe.log_error(
			message=frappe.get_traceback(),
			title=f"Get Payment Status Error - {gateway}",
		)
		return {"status": "Error", "message": "Failed to get payment status"}
