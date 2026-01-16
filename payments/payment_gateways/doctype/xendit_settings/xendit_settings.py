# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.integrations.utils import create_request_log
from frappe.model.document import Document

from payments.payment_gateways.xendit.constants import DEFAULT_INVOICE_DURATION, SUPPORTED_CURRENCIES
from payments.payment_gateways.xendit.invoice_api import XenditInvoiceAPI


class XenditSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		callback_token: DF.Password
		gateway_name: DF.Data | None
		invoice_duration: DF.Int
		payment_account: DF.Link | None
		redirect_to: DF.Data | None
		reminder_time: DF.Int
		secret_key: DF.Password
	# end: auto-generated types

	supported_currencies = SUPPORTED_CURRENCIES

	def validate(self):
		"""Validate settings and create payment gateway record."""
		self.setup_payment_gateway()

	def setup_payment_gateway(self):
		"""
		Create or update Payment Gateway record for Xendit.

		For Single DocType like Xendit Settings, we must NOT set gateway_settings
		and gateway_controller fields, as Single DocTypes are not valid for Dynamic Links.
		The system will fallback to using "{gateway_name} Settings" pattern.
		"""
		gateway_name = "Xendit"

		if not frappe.db.exists("Payment Gateway", gateway_name):
			# Create new record without gateway_settings
			frappe.get_doc({
				"doctype": "Payment Gateway",
				"gateway": gateway_name,
				"gateway_settings": None,
				"gateway_controller": None,
			}).insert(ignore_permissions=True)
		else:
			# Use direct SQL to avoid validation errors with Dynamic Link
			frappe.db.sql(
				"""
				UPDATE `tabPayment Gateway`
				SET gateway_settings = NULL, gateway_controller = NULL
				WHERE gateway = %s AND (gateway_settings IS NOT NULL OR gateway_controller IS NOT NULL)
				""",
				gateway_name,
			)

	def validate_transaction_currency(self, currency: str) -> None:
		"""
		Validate if the currency is supported.

		Args:
		    currency: Currency code to validate

		Raises:
		    frappe.ValidationError if currency is not supported
		"""
		if currency not in self.supported_currencies:
			frappe.throw(
				_(
					"Currency {0} is not supported by Xendit. Supported currencies: {1}"
				).format(currency, ", ".join(self.supported_currencies))
			)

	def get_payment_url(self, **kwargs) -> str:
		"""
		Generate Xendit Invoice payment URL.

		Args:
		    kwargs:
		        - amount (float): Payment amount
		        - reference_doctype (str): Reference document type
		        - reference_docname (str): Reference document name
		        - payer_email (str): Customer email
		        - payer_name (str): Customer name
		        - description (str): Payment description
		        - currency (str): Currency code (default: IDR)

		Returns:
		    str: Xendit Invoice URL
		"""
		try:
			# Validate required parameters
			amount = kwargs.get("amount")
			reference_doctype = kwargs.get("reference_doctype")
			reference_docname = kwargs.get("reference_docname")
			payer_email = kwargs.get("payer_email")

			if not amount:
				frappe.throw(_("Amount is required"))

			if not reference_doctype or not reference_docname:
				frappe.throw(_("Reference document is required"))

			if not payer_email:
				frappe.throw(_("Payer email is required"))

			# Validate currency
			currency = kwargs.get("currency", "IDR")
			self.validate_transaction_currency(currency)

			# Create Integration Request for tracking
			integration_request = create_request_log(kwargs, service_name="Xendit")

			# Generate unique external ID
			external_id = f"{reference_doctype}-{reference_docname}-{integration_request.name}"

			# Build customer details
			payer_name = kwargs.get("payer_name", "Customer")
			name_parts = payer_name.split() if payer_name else ["Customer"]
			customer = {
				"given_names": name_parts[0],
				"surname": name_parts[-1] if len(name_parts) > 1 else "",
				"email": payer_email,
				"mobile_number": kwargs.get("payer_phone", ""),
			}

			# Build redirect URLs
			site_url = frappe.utils.get_url()
			success_redirect_url = kwargs.get("redirect_to") or self.redirect_to or f"{site_url}/payment-success"
			failure_redirect_url = f"{site_url}/payment-failed"

			# Get invoice duration
			invoice_duration = self.invoice_duration or DEFAULT_INVOICE_DURATION

			# Initialize Xendit API
			secret_key = self.get_password("secret_key")
			api = XenditInvoiceAPI(secret_key=secret_key)

			# Create invoice
			description = kwargs.get("description") or f"Payment for {reference_docname}"
			response = api.create_invoice(
				external_id=external_id,
				amount=float(amount),
				payer_email=payer_email,
				description=description,
				customer=customer,
				invoice_duration=invoice_duration,
				success_redirect_url=success_redirect_url,
				failure_redirect_url=failure_redirect_url,
				currency=currency,
			)

			# Update Integration Request with Xendit data
			integration_request_dict = frappe.parse_json(integration_request.data)
			integration_request_dict.update({
				"xendit_external_id": external_id,
				"xendit_invoice_id": response.get("id"),
				"xendit_invoice_url": response.get("invoice_url"),
				"redirect_to": success_redirect_url,
			})
			integration_request.data = frappe.as_json(integration_request_dict)
			integration_request.save(ignore_permissions=True)
			frappe.db.commit()

			return response.get("invoice_url")

		except Exception:
			frappe.log_error(
				message=frappe.get_traceback(),
				title="Xendit Payment URL Error",
			)
			frappe.throw(_("Failed to generate Xendit payment URL. Please try again."))

	def create_order(self, **kwargs) -> dict:
		"""
		Create a Xendit invoice (alias for get_payment_url for compatibility).

		Returns:
		    dict containing order details and invoice URL
		"""
		invoice_url = self.get_payment_url(**kwargs)
		return {
			"invoice_url": invoice_url,
			"status": "Created",
		}
