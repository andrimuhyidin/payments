# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.integrations.utils import create_request_log
from frappe.model.document import Document

from payments.payment_gateways.midtrans.constants import SUPPORTED_CURRENCIES
from payments.payment_gateways.midtrans.snap_api import MidtransSnapAPI


class MidtransSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		client_key: DF.Data
		gateway_name: DF.Data | None
		is_sandbox: DF.Check
		merchant_id: DF.Data | None
		payment_account: DF.Link | None
		redirect_to: DF.Data | None
		server_key: DF.Password
	# end: auto-generated types

	supported_currencies = SUPPORTED_CURRENCIES

	def validate(self):
		"""Validate settings and create payment gateway record."""
		self.setup_payment_gateway()

	def setup_payment_gateway(self):
		"""
		Create or update Payment Gateway record for Midtrans.

		For Single DocType like Midtrans Settings, we must NOT set gateway_settings
		and gateway_controller fields, as Single DocTypes are not valid for Dynamic Links.
		The system will fallback to using "{gateway_name} Settings" pattern.
		"""
		gateway_name = "Midtrans"

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
					"Currency {0} is not supported by Midtrans. Supported currencies: {1}"
				).format(currency, ", ".join(self.supported_currencies))
			)

	def get_payment_url(self, **kwargs) -> str:
		"""
		Generate Midtrans Snap payment URL.

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
		    str: Midtrans Snap redirect URL
		"""
		try:
			# Validate required parameters
			amount = kwargs.get("amount")
			reference_doctype = kwargs.get("reference_doctype")
			reference_docname = kwargs.get("reference_docname")

			if not amount:
				frappe.throw(_("Amount is required"))

			if not reference_doctype or not reference_docname:
				frappe.throw(_("Reference document is required"))

			# Validate currency
			currency = kwargs.get("currency", "IDR")
			self.validate_transaction_currency(currency)

			# Create Integration Request for tracking
			integration_request = create_request_log(kwargs, service_name="Midtrans")

			# Generate unique order ID
			order_id = f"{reference_doctype}-{reference_docname}-{integration_request.name}"

			# Convert amount to integer (Midtrans requires integer amount)
			gross_amount = int(float(amount))

			# Build customer details
			payer_name = kwargs.get("payer_name", "Customer")
			name_parts = payer_name.split() if payer_name else ["Customer"]
			customer_details = {
				"first_name": name_parts[0],
				"last_name": name_parts[-1] if len(name_parts) > 1 else "",
				"email": kwargs.get("payer_email", ""),
				"phone": kwargs.get("payer_phone", ""),
			}

			# Build callbacks
			site_url = frappe.utils.get_url()
			callbacks = {
				"finish": kwargs.get("redirect_to") or self.redirect_to or f"{site_url}/payment-success",
				"error": f"{site_url}/payment-failed",
				"pending": f"{site_url}/payment-pending",
			}

			# Initialize Midtrans API
			server_key = self.get_password("server_key")
			api = MidtransSnapAPI(server_key=server_key, is_sandbox=bool(self.is_sandbox))

			# Create transaction
			response = api.create_transaction(
				order_id=order_id,
				gross_amount=gross_amount,
				customer_details=customer_details,
				callbacks=callbacks,
			)

			# Update Integration Request with Midtrans data
			integration_request_dict = frappe.parse_json(integration_request.data)
			integration_request_dict.update({
				"midtrans_order_id": order_id,
				"midtrans_token": response.get("token"),
				"redirect_url": response.get("redirect_url"),
			})
			integration_request.data = frappe.as_json(integration_request_dict)
			integration_request.save(ignore_permissions=True)
			frappe.db.commit()

			return response.get("redirect_url")

		except Exception:
			frappe.log_error(
				message=frappe.get_traceback(),
				title="Midtrans Payment URL Error",
			)
			frappe.throw(_("Failed to generate Midtrans payment URL. Please try again."))

	def create_order(self, **kwargs) -> dict:
		"""
		Create a Midtrans order (alias for get_payment_url for compatibility).

		Returns:
		    dict containing order details and redirect URL
		"""
		redirect_url = self.get_payment_url(**kwargs)
		return {
			"redirect_url": redirect_url,
			"status": "Created",
		}
