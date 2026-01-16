# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import base64

import frappe
from frappe import _
from frappe.integrations.utils import make_post_request

from payments.payment_gateways.xendit.constants import (
	DEFAULT_INVOICE_DURATION,
	XENDIT_API_BASE_URL,
	XENDIT_INVOICE_URL,
)


class XenditInvoiceAPI:
	"""API client for Xendit Invoice integration."""

	def __init__(self, secret_key: str):
		"""
		Initialize Xendit Invoice API client.

		Args:
		    secret_key: Secret key from Xendit Dashboard
		"""
		self.secret_key = secret_key
		self.base_url = XENDIT_API_BASE_URL
		self.invoice_url = XENDIT_INVOICE_URL

	def _get_auth_header(self) -> str:
		"""Generate Base64 encoded authorization header."""
		auth_string = base64.b64encode(f"{self.secret_key}:".encode()).decode()
		return f"Basic {auth_string}"

	def _get_headers(self) -> dict:
		"""Get request headers with authorization."""
		return {
			"Content-Type": "application/json",
			"Authorization": self._get_auth_header(),
		}

	def create_invoice(
		self,
		external_id: str,
		amount: float,
		payer_email: str,
		description: str = "",
		customer: dict | None = None,
		invoice_duration: int = DEFAULT_INVOICE_DURATION,
		success_redirect_url: str = "",
		failure_redirect_url: str = "",
		currency: str = "IDR",
		items: list | None = None,
		fees: list | None = None,
	) -> dict:
		"""
		Create a Xendit invoice.

		Args:
		    external_id: Unique external identifier for the invoice
		    amount: Invoice amount
		    payer_email: Customer email address
		    description: Invoice description
		    customer: Customer details object
		    invoice_duration: Invoice expiry in seconds
		    success_redirect_url: URL to redirect after successful payment
		    failure_redirect_url: URL to redirect after failed payment
		    currency: Currency code (IDR, PHP, USD)
		    items: List of items in the invoice
		    fees: Additional fees

		Returns:
		    dict containing invoice details including invoice_url
		"""
		payload = {
			"external_id": external_id,
			"amount": float(amount),
			"payer_email": payer_email,
			"description": description or f"Payment for {external_id}",
			"invoice_duration": invoice_duration,
			"currency": currency,
		}

		if customer:
			payload["customer"] = customer

		if success_redirect_url:
			payload["success_redirect_url"] = success_redirect_url

		if failure_redirect_url:
			payload["failure_redirect_url"] = failure_redirect_url

		if items:
			payload["items"] = items

		if fees:
			payload["fees"] = fees

		try:
			response = make_post_request(
				url=self.invoice_url,
				headers=self._get_headers(),
				json=payload,
			)

			if not response:
				frappe.throw(_("Empty response from Xendit"))

			if "error_code" in response:
				error_msg = response.get("message", "Unknown error")
				frappe.throw(_("Xendit Error: {0}").format(error_msg))

			return response

		except Exception as e:
			frappe.log_error(
				message=frappe.get_traceback(),
				title="Xendit Invoice API Error",
			)
			frappe.throw(_("Failed to create Xendit invoice: {0}").format(str(e)))

	def get_invoice(self, invoice_id: str) -> dict:
		"""
		Get invoice details by ID.

		Args:
		    invoice_id: Xendit invoice ID

		Returns:
		    dict containing invoice details
		"""
		from frappe.integrations.utils import make_get_request

		url = f"{self.invoice_url}/{invoice_id}"

		try:
			response = make_get_request(url, headers=self._get_headers())
			return response
		except Exception as e:
			frappe.log_error(
				message=frappe.get_traceback(),
				title="Xendit Get Invoice Error",
			)
			frappe.throw(_("Failed to get invoice: {0}").format(str(e)))

	def expire_invoice(self, invoice_id: str) -> dict:
		"""
		Expire an invoice manually.

		Args:
		    invoice_id: Xendit invoice ID to expire

		Returns:
		    dict containing expired invoice details
		"""
		url = f"{self.invoice_url}/{invoice_id}/expire!"

		try:
			response = make_post_request(
				url=url,
				headers=self._get_headers(),
				json={},
			)
			return response
		except Exception as e:
			frappe.log_error(
				message=frappe.get_traceback(),
				title="Xendit Expire Invoice Error",
			)
			frappe.throw(_("Failed to expire invoice: {0}").format(str(e)))
