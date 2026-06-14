# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

"""Unit tests for the Xendit QR Codes API client.

These mock the HTTP transport (``make_post_request`` / ``make_get_request``) so
they exercise request CONSTRUCTION and response PARSING without a live Xendit
secret_key — the bench has none, so end-to-end is intentionally out of scope.
"""

import base64
import unittest
from unittest.mock import patch

from payments.payment_gateways.xendit.qr_api import (
	XENDIT_QR_API_VERSION,
	XENDIT_QR_URL,
	XenditQRCodeAPI,
)


class TestXenditQRCodeAPI(unittest.TestCase):
	def test_qr_url(self):
		self.assertEqual(XENDIT_QR_URL, "https://api.xendit.co/qr_codes")

	def test_auth_header_generation(self):
		secret_key = "xnd_development_test_key"
		api = XenditQRCodeAPI(secret_key=secret_key)
		expected = f"Basic {base64.b64encode(f'{secret_key}:'.encode()).decode()}"
		self.assertEqual(api._get_auth_header(), expected)

	def test_headers_include_api_version(self):
		api = XenditQRCodeAPI(secret_key="test_key")
		headers = api._get_headers()
		self.assertEqual(headers["Content-Type"], "application/json")
		self.assertTrue(headers["Authorization"].startswith("Basic "))
		self.assertEqual(headers["api-version"], XENDIT_QR_API_VERSION)

	@patch("payments.payment_gateways.xendit.qr_api.make_post_request")
	def test_create_qr_code_request_construction(self, mock_post):
		"""The request must hit /qr_codes with a DYNAMIC IDR payload + amount."""
		mock_post.return_value = {
			"id": "qr_abc123",
			"qr_string": "00020101021226...",
			"status": "ACTIVE",
			"amount": 150000,
			"currency": "IDR",
			"expires_at": "2026-06-14T12:00:00Z",
		}
		api = XenditQRCodeAPI(secret_key="test_key")
		resp = api.create_qr_code(
			reference_id="LOKET-BK-1",
			amount=150000.0,
			expires_at="2026-06-14T12:00:00Z",
		)

		# called exactly once, against the QR endpoint
		mock_post.assert_called_once()
		_, kwargs = mock_post.call_args
		self.assertEqual(kwargs["url"], XENDIT_QR_URL)
		self.assertEqual(kwargs["headers"]["api-version"], XENDIT_QR_API_VERSION)

		sent = kwargs["json"]
		self.assertEqual(sent["reference_id"], "LOKET-BK-1")
		self.assertEqual(sent["type"], "DYNAMIC")
		self.assertEqual(sent["currency"], "IDR")
		self.assertEqual(sent["amount"], 150000.0)
		self.assertEqual(sent["expires_at"], "2026-06-14T12:00:00Z")

		# response parsing
		self.assertEqual(resp["id"], "qr_abc123")
		self.assertEqual(resp["qr_string"], "00020101021226...")
		self.assertEqual(resp["status"], "ACTIVE")

	@patch("payments.payment_gateways.xendit.qr_api.make_post_request")
	def test_create_qr_code_omits_expiry_when_absent(self, mock_post):
		mock_post.return_value = {"id": "qr_x", "qr_string": "x", "status": "ACTIVE"}
		api = XenditQRCodeAPI(secret_key="test_key")
		api.create_qr_code(reference_id="REF", amount=1000.0)
		_, kwargs = mock_post.call_args
		self.assertNotIn("expires_at", kwargs["json"])

	@patch("payments.payment_gateways.xendit.qr_api.make_post_request")
	def test_create_qr_code_raises_on_error_code(self, mock_post):
		import frappe

		mock_post.return_value = {
			"error_code": "INVALID_API_KEY",
			"message": "API key is invalid",
		}
		api = XenditQRCodeAPI(secret_key="bad")
		with self.assertRaises(frappe.exceptions.ValidationError):
			api.create_qr_code(reference_id="REF", amount=1000.0)

	@patch("payments.payment_gateways.xendit.qr_api.make_get_request")
	def test_get_qr_code(self, mock_get):
		mock_get.return_value = {"id": "qr_1", "status": "ACTIVE", "qr_string": "y"}
		api = XenditQRCodeAPI(secret_key="test_key")
		resp = api.get_qr_code("qr_1")
		mock_get.assert_called_once()
		args, kwargs = mock_get.call_args
		self.assertEqual(args[0], f"{XENDIT_QR_URL}/qr_1")
		self.assertEqual(resp["status"], "ACTIVE")


if __name__ == "__main__":
	unittest.main()
