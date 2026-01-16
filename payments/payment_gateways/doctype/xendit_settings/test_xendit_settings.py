# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import unittest

from frappe.tests.utils import FrappeTestCase

from payments.payment_gateways.xendit.callback_validator import (
	XenditCallbackValidator,
	validate_xendit_callback,
)
from payments.payment_gateways.xendit.constants import (
	INVOICE_STATUS_PAID,
	INVOICE_STATUS_SETTLED,
	SUCCESSFUL_STATUSES,
	SUPPORTED_CURRENCIES,
	XENDIT_API_BASE_URL,
	XENDIT_INVOICE_URL,
)


class TestXenditSettings(FrappeTestCase):
	"""Test cases for Xendit Settings DocType."""

	pass


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

	def test_supported_currencies(self):
		"""Test supported currencies include IDR."""
		self.assertIn("IDR", SUPPORTED_CURRENCIES)
		self.assertIn("PHP", SUPPORTED_CURRENCIES)
		self.assertIn("USD", SUPPORTED_CURRENCIES)

	def test_invoice_status_constants(self):
		"""Test invoice status constants."""
		self.assertEqual(INVOICE_STATUS_PAID, "PAID")
		self.assertEqual(INVOICE_STATUS_SETTLED, "SETTLED")
