# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import unittest
from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

from payments.payment_gateways.xendit.callback_validator import (
	XenditCallbackValidator,
	validate_xendit_callback,
)
from payments.payment_gateways.xendit.constants import (
	DEFAULT_INVOICE_DURATION,
	INVOICE_STATUS_PAID,
	INVOICE_STATUS_PENDING,
	INVOICE_STATUS_SETTLED,
	INVOICE_STATUS_EXPIRED,
	SUCCESSFUL_STATUSES,
	FAILED_STATUSES,
	SUPPORTED_CURRENCIES,
	PAYMENT_METHODS,
	XENDIT_API_BASE_URL,
	XENDIT_INVOICE_URL,
)
from payments.payment_gateways.xendit.invoice_api import XenditInvoiceAPI


class TestXenditSettings(FrappeTestCase):
	"""Test cases for Xendit Settings DocType."""

	def test_supported_currencies(self):
		"""Test that IDR, PHP, and USD are in supported currencies."""
		self.assertIn("IDR", SUPPORTED_CURRENCIES)
		self.assertIn("PHP", SUPPORTED_CURRENCIES)
		self.assertIn("USD", SUPPORTED_CURRENCIES)

	def test_successful_statuses(self):
		"""Test successful invoice statuses."""
		self.assertIn(INVOICE_STATUS_PAID, SUCCESSFUL_STATUSES)
		self.assertIn(INVOICE_STATUS_SETTLED, SUCCESSFUL_STATUSES)

	def test_failed_statuses(self):
		"""Test failed invoice statuses."""
		self.assertIn(INVOICE_STATUS_EXPIRED, FAILED_STATUSES)

	def test_default_invoice_duration(self):
		"""Test default invoice duration is 24 hours."""
		self.assertEqual(DEFAULT_INVOICE_DURATION, 86400)


class TestXenditCallbackValidator(unittest.TestCase):
	"""Test cases for Xendit callback token validation."""

	def test_valid_callback_token(self):
		"""Test that a matching callback token passes validation."""
		callback_token = "xnd_test_callback_token_123"
		incoming_token = "xnd_test_callback_token_123"

		validator = XenditCallbackValidator(
			callback_token=callback_token,
			incoming_token=incoming_token,
		)

		self.assertTrue(validator.is_valid)

	def test_invalid_callback_token(self):
		"""Test that a non-matching callback token fails validation."""
		callback_token = "xnd_test_callback_token_123"
		incoming_token = "wrong_token"

		validator = XenditCallbackValidator(
			callback_token=callback_token,
			incoming_token=incoming_token,
		)

		self.assertFalse(validator.is_valid)

	def test_empty_callback_token(self):
		"""Test that empty tokens fail validation."""
		validator = XenditCallbackValidator(
			callback_token="",
			incoming_token="some_token",
		)
		self.assertFalse(validator.is_valid)

		validator = XenditCallbackValidator(
			callback_token="some_token",
			incoming_token="",
		)
		self.assertFalse(validator.is_valid)

	def test_none_callback_token(self):
		"""Test that None tokens fail validation."""
		validator = XenditCallbackValidator(
			callback_token=None,
			incoming_token="some_token",
		)
		self.assertFalse(validator.is_valid)

	def test_whitespace_tokens(self):
		"""Test that whitespace-only tokens fail validation."""
		validator = XenditCallbackValidator(
			callback_token="   ",
			incoming_token="some_token",
		)
		# Whitespace is truthy but not equal to the token
		self.assertFalse(validator.is_valid)

	def test_case_sensitive_validation(self):
		"""Test that token validation is case-sensitive."""
		callback_token = "xnd_Test_Token"
		incoming_token = "xnd_test_token"

		validator = XenditCallbackValidator(
			callback_token=callback_token,
			incoming_token=incoming_token,
		)

		self.assertFalse(validator.is_valid)

	def test_convenience_function(self):
		"""Test the validate_xendit_callback convenience function."""
		callback_token = "xnd_callback_token_456"

		# Test valid token
		self.assertTrue(
			validate_xendit_callback(
				callback_token=callback_token,
				incoming_token=callback_token,
			)
		)

		# Test invalid token
		self.assertFalse(
			validate_xendit_callback(
				callback_token=callback_token,
				incoming_token="wrong_token",
			)
		)


class TestXenditInvoiceAPI(unittest.TestCase):
	"""Test cases for Xendit Invoice API client."""

	def test_api_url_configuration(self):
		"""Test that API URLs are correctly configured."""
		api = XenditInvoiceAPI(secret_key="test_secret_key")
		self.assertEqual(api.base_url, XENDIT_API_BASE_URL)
		self.assertEqual(api.invoice_url, XENDIT_INVOICE_URL)

	def test_auth_header_generation(self):
		"""Test that authorization header is correctly generated."""
		import base64

		secret_key = "xnd_development_test_key"
		api = XenditInvoiceAPI(secret_key=secret_key)

		expected_auth = f"Basic {base64.b64encode(f'{secret_key}:'.encode()).decode()}"
		self.assertEqual(api._get_auth_header(), expected_auth)

	def test_headers_structure(self):
		"""Test that request headers have correct structure."""
		api = XenditInvoiceAPI(secret_key="test_key")
		headers = api._get_headers()

		self.assertIn("Content-Type", headers)
		self.assertIn("Authorization", headers)
		self.assertEqual(headers["Content-Type"], "application/json")
		self.assertTrue(headers["Authorization"].startswith("Basic "))


class TestXenditConstants(unittest.TestCase):
	"""Test cases for Xendit constants."""

	def test_api_base_url(self):
		"""Test API base URL is correct."""
		self.assertEqual(XENDIT_API_BASE_URL, "https://api.xendit.co")

	def test_invoice_url(self):
		"""Test invoice URL is correct."""
		self.assertEqual(XENDIT_INVOICE_URL, "https://api.xendit.co/v2/invoices")

	def test_successful_statuses(self):
		"""Test successful statuses include expected values."""
		self.assertIn(INVOICE_STATUS_PAID, SUCCESSFUL_STATUSES)
		self.assertIn(INVOICE_STATUS_SETTLED, SUCCESSFUL_STATUSES)

	def test_failed_statuses(self):
		"""Test failed statuses include expected values."""
		self.assertIn(INVOICE_STATUS_EXPIRED, FAILED_STATUSES)

	def test_invoice_status_constants(self):
		"""Test invoice status constants."""
		self.assertEqual(INVOICE_STATUS_PAID, "PAID")
		self.assertEqual(INVOICE_STATUS_SETTLED, "SETTLED")
		self.assertEqual(INVOICE_STATUS_PENDING, "PENDING")
		self.assertEqual(INVOICE_STATUS_EXPIRED, "EXPIRED")

	def test_supported_currencies(self):
		"""Test supported currencies include IDR."""
		self.assertIn("IDR", SUPPORTED_CURRENCIES)
		self.assertIn("PHP", SUPPORTED_CURRENCIES)
		self.assertIn("USD", SUPPORTED_CURRENCIES)

	def test_payment_methods_not_empty(self):
		"""Test that payment methods list is not empty."""
		self.assertTrue(len(PAYMENT_METHODS) > 0)

	def test_common_payment_methods_present(self):
		"""Test that common Indonesian payment methods are present."""
		common_methods = ["BCA", "BNI", "BRI", "MANDIRI", "OVO", "DANA", "QRIS"]
		for method in common_methods:
			self.assertIn(method, PAYMENT_METHODS)

	def test_default_invoice_duration(self):
		"""Test default invoice duration is 24 hours (86400 seconds)."""
		self.assertEqual(DEFAULT_INVOICE_DURATION, 86400)
