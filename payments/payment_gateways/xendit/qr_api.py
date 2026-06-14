# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

"""Xendit QR Codes API client.

Wraps the Xendit ``/qr_codes`` endpoint, which creates a *dynamic* QRIS charge
and returns a raw ``qr_string`` (the EMVCo payload renderable as a QR at a
counter), as opposed to the Invoice API (``/v2/invoices``) which returns a
hosted-checkout ``invoice_url``.

Reference: https://developer.xendit.co/api-reference/#qr-code (Create QR Code).
Request (JSON):
    {
      "reference_id": "<unique id>",
      "type": "DYNAMIC",
      "currency": "IDR",
      "amount": <number>,          # MAJOR units (IDR rupiah)
      "expires_at": "<ISO8601>",   # optional
    }
Headers:
    Authorization: Basic base64("<secret_key>:")
    api-version: 2022-07-31        # QR Codes API requires an explicit version

Response (relevant fields):
    { "id": "qr_...", "qr_string": "0002010102...", "status": "ACTIVE",
      "amount": 10000, "currency": "IDR", "expires_at": "..." }
"""

import base64

import frappe
from frappe import _
from frappe.integrations.utils import make_get_request, make_post_request

from payments.payment_gateways.xendit.constants import XENDIT_API_BASE_URL

XENDIT_QR_URL = f"{XENDIT_API_BASE_URL}/qr_codes"
# Xendit pins QR Codes behind a dated API version; the create-QR shape below is
# the 2022-07-31 contract.
XENDIT_QR_API_VERSION = "2022-07-31"


class XenditQRCodeAPI:
	"""API client for the Xendit QR Codes (QRIS) integration."""

	def __init__(self, secret_key: str):
		"""
		Args:
		    secret_key: Secret key from the Xendit Dashboard.
		"""
		self.secret_key = secret_key
		self.qr_url = XENDIT_QR_URL

	def _get_auth_header(self) -> str:
		"""Base64-encoded HTTP Basic auth header (secret_key as username, no password)."""
		auth_string = base64.b64encode(f"{self.secret_key}:".encode()).decode()
		return f"Basic {auth_string}"

	def _get_headers(self) -> dict:
		return {
			"Content-Type": "application/json",
			"Authorization": self._get_auth_header(),
			"api-version": XENDIT_QR_API_VERSION,
		}

	def create_qr_code(
		self,
		reference_id: str,
		amount: float,
		currency: str = "IDR",
		qr_type: str = "DYNAMIC",
		expires_at: str | None = None,
		callback_url: str | None = None,
	) -> dict:
		"""
		Create a dynamic QRIS charge and return its raw ``qr_string``.

		Args:
		    reference_id: Unique merchant reference for this charge.
		    amount: Charge amount in MAJOR units (IDR rupiah).
		    currency: Currency code (QRIS → "IDR").
		    qr_type: "DYNAMIC" (amount-bound, single use) or "STATIC".
		    expires_at: optional ISO-8601 expiry timestamp.
		    callback_url: optional per-charge webhook URL. Xendit POSTs the
		        ``qr.payment`` event here on settlement (overrides the
		        account-level QR callback configured in the dashboard).

		Returns:
		    dict with at least ``id``, ``qr_string``, ``status``, ``amount``,
		    ``currency``, ``expires_at`` (raw Xendit response).
		"""
		payload = {
			"reference_id": reference_id,
			"type": qr_type,
			"currency": currency,
			"amount": float(amount),
		}
		if expires_at:
			payload["expires_at"] = expires_at
		if callback_url:
			payload["callback_url"] = callback_url

		try:
			response = make_post_request(
				url=self.qr_url,
				headers=self._get_headers(),
				json=payload,
			)

			if not response:
				frappe.throw(_("Empty response from Xendit QR Codes API"))

			# Xendit returns error_code on failure (4xx/5xx mapped through the util).
			if "error_code" in response:
				error_msg = response.get("message", "Unknown error")
				frappe.throw(_("Xendit QR Error: {0}").format(error_msg))

			return response

		except Exception as e:
			# M5: do NOT log full traceback — local frames hold the Basic-auth
			# header (secret_key). Log only the exception type.
			frappe.log_error(
				message=f"Xendit QR create failed: {type(e).__name__}",
				title="Xendit QR Codes API Error",
			)
			frappe.throw(_("Failed to create Xendit QR code: {0}").format(type(e).__name__))

	def get_qr_code(self, qr_id: str) -> dict:
		"""
		Fetch a QR code by its Xendit id.

		Args:
		    qr_id: Xendit QR code id (``qr_...``).

		Returns:
		    dict with the QR code details (status, qr_string, amount, ...).
		"""
		url = f"{self.qr_url}/{qr_id}"
		try:
			return make_get_request(url, headers=self._get_headers())
		except Exception as e:
			# M5: avoid logging full traceback (may capture the auth header secret).
			frappe.log_error(
				message=f"Xendit QR get failed: {type(e).__name__}",
				title="Xendit Get QR Code Error",
			)
			frappe.throw(_("Failed to get QR code: {0}").format(type(e).__name__))
