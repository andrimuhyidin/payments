# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import base64

import frappe
from frappe import _
from frappe.integrations.utils import make_post_request

from payments.payment_gateways.midtrans.constants import (
	MIDTRANS_PRODUCTION_SNAP_URL,
	MIDTRANS_SANDBOX_SNAP_URL,
)


class MidtransSnapAPI:
	"""API client for Midtrans Snap integration."""

	def __init__(self, server_key: str, is_sandbox: bool = True):
		"""
		Initialize Midtrans Snap API client.

		Args:
		    server_key: Server key from Midtrans Dashboard
		    is_sandbox: Use sandbox environment if True
		"""
		self.server_key = server_key
		self.is_sandbox = is_sandbox
		self.base_url = MIDTRANS_SANDBOX_SNAP_URL if is_sandbox else MIDTRANS_PRODUCTION_SNAP_URL

	def _get_auth_header(self) -> str:
		"""Generate Base64 encoded authorization header."""
		auth_string = base64.b64encode(f"{self.server_key}:".encode()).decode()
		return f"Basic {auth_string}"

	def _get_headers(self) -> dict:
		"""Get request headers with authorization."""
		return {
			"Content-Type": "application/json",
			"Accept": "application/json",
			"Authorization": self._get_auth_header(),
		}

	def create_transaction(
		self,
		order_id: str,
		gross_amount: int,
		customer_details: dict | None = None,
		item_details: list | None = None,
		enabled_payments: list | None = None,
		callbacks: dict | None = None,
	) -> dict:
		"""
		Create a Snap transaction and get redirect URL.

		Args:
		    order_id: Unique order identifier
		    gross_amount: Transaction amount in IDR (integer, no decimals)
		    customer_details: Customer information (first_name, last_name, email, phone)
		    item_details: List of items in the transaction
		    enabled_payments: List of enabled payment methods
		    callbacks: Callback URLs (finish, error, pending)

		Returns:
		    dict containing token and redirect_url
		"""
		payload = {
			"transaction_details": {
				"order_id": order_id,
				"gross_amount": int(gross_amount),  # Must be integer
			},
			"credit_card": {
				"secure": True,
			},
		}

		if customer_details:
			payload["customer_details"] = customer_details

		if item_details:
			payload["item_details"] = item_details

		if enabled_payments:
			payload["enabled_payments"] = enabled_payments

		if callbacks:
			payload["callbacks"] = callbacks

		try:
			response = make_post_request(
				url=self.base_url,
				headers=self._get_headers(),
				json=payload,
			)

			if not response:
				frappe.throw(_("Empty response from Midtrans"))

			if "error_messages" in response:
				error_msg = ", ".join(response.get("error_messages", []))
				frappe.throw(_("Midtrans Error: {0}").format(error_msg))

			return response

		except Exception as e:
			frappe.log_error(
				message=frappe.get_traceback(),
				title="Midtrans Snap API Error",
			)
			frappe.throw(_("Failed to create Midtrans transaction: {0}").format(str(e)))

	def get_transaction_status(self, order_id: str) -> dict:
		"""
		Get transaction status from Midtrans.

		Args:
		    order_id: The order ID to check

		Returns:
		    dict containing transaction status
		"""
		from frappe.integrations.utils import make_get_request

		from payments.payment_gateways.midtrans.constants import (
			MIDTRANS_PRODUCTION_API_URL,
			MIDTRANS_SANDBOX_API_URL,
		)

		api_url = MIDTRANS_SANDBOX_API_URL if self.is_sandbox else MIDTRANS_PRODUCTION_API_URL
		url = f"{api_url}/{order_id}/status"

		try:
			response = make_get_request(url, headers=self._get_headers())
			return response
		except Exception as e:
			frappe.log_error(
				message=frappe.get_traceback(),
				title="Midtrans Status Check Error",
			)
			frappe.throw(_("Failed to get transaction status: {0}").format(str(e)))
