# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import hashlib
import unittest
from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

from payments.payment_gateways.midtrans.constants import (
	MIDTRANS_PRODUCTION_SNAP_URL,
	MIDTRANS_SANDBOX_SNAP_URL,
	SUCCESSFUL_STATUSES,
	FAILED_STATUSES,
	TRANSACTION_STATUS_SETTLEMENT,
	TRANSACTION_STATUS_CAPTURE,
	TRANSACTION_STATUS_DENY,
	TRANSACTION_STATUS_EXPIRE,
	SUPPORTED_CURRENCIES,
)
from payments.payment_gateways.midtrans.signature_validator import (
	MidtransSignatureValidator,
	validate_midtrans_signature,
)
from payments.payment_gateways.midtrans.snap_api import MidtransSnapAPI


class TestMidtransSettings(FrappeTestCase):
	"""Test cases for Midtrans Settings DocType."""

	def test_supported_currencies(self):
		"""Test that IDR is in supported currencies."""
		self.assertIn("IDR", SUPPORTED_CURRENCIES)

	def test_successful_statuses(self):
		"""Test successful transaction statuses."""
		self.assertIn(TRANSACTION_STATUS_CAPTURE, SUCCESSFUL_STATUSES)
		self.assertIn(TRANSACTION_STATUS_SETTLEMENT, SUCCESSFUL_STATUSES)

	def test_failed_statuses(self):
		"""Test failed transaction statuses."""
		self.assertIn(TRANSACTION_STATUS_DENY, FAILED_STATUSES)
		self.assertIn(TRANSACTION_STATUS_EXPIRE, FAILED_STATUSES)


class TestMidtransSignatureValidator(unittest.TestCase):
	"""Test cases for Midtrans signature validation."""

	def test_valid_signature(self):
		"""Test that a correctly generated signature passes validation."""
		order_id = "ORDER-001"
		status_code = "200"
		gross_amount = "100000.00"
		server_key = "SB-Mid-server-test123"

		# Generate the expected signature
		signature_string = f"{order_id}{status_code}{gross_amount}{server_key}"
		expected_signature = hashlib.sha512(signature_string.encode()).hexdigest()

		validator = MidtransSignatureValidator(
			order_id=order_id,
			status_code=status_code,
			gross_amount=gross_amount,
			server_key=server_key,
			signature_key=expected_signature,
		)

		self.assertTrue(validator.is_valid)

	def test_invalid_signature(self):
		"""Test that an invalid signature fails validation."""
		validator = MidtransSignatureValidator(
			order_id="ORDER-001",
			status_code="200",
			gross_amount="100000.00",
			server_key="SB-Mid-server-test123",
			signature_key="invalid_signature_key",
		)

		self.assertFalse(validator.is_valid)

	def test_signature_with_different_amounts(self):
		"""Test signature validation with different gross amounts."""
		order_id = "ORDER-002"
		status_code = "200"
		server_key = "SB-Mid-server-test456"

		# Test with integer amount
		gross_amount_1 = "50000"
		signature_string_1 = f"{order_id}{status_code}{gross_amount_1}{server_key}"
		signature_1 = hashlib.sha512(signature_string_1.encode()).hexdigest()

		validator_1 = MidtransSignatureValidator(
			order_id=order_id,
			status_code=status_code,
			gross_amount=gross_amount_1,
			server_key=server_key,
			signature_key=signature_1,
		)
		self.assertTrue(validator_1.is_valid)

		# Test with decimal amount
		gross_amount_2 = "50000.50"
		signature_string_2 = f"{order_id}{status_code}{gross_amount_2}{server_key}"
		signature_2 = hashlib.sha512(signature_string_2.encode()).hexdigest()

		validator_2 = MidtransSignatureValidator(
			order_id=order_id,
			status_code=status_code,
			gross_amount=gross_amount_2,
			server_key=server_key,
			signature_key=signature_2,
		)
		self.assertTrue(validator_2.is_valid)

	def test_convenience_function(self):
		"""Test the validate_midtrans_signature convenience function."""
		order_id = "ORDER-002"
		status_code = "200"
		gross_amount = "50000.00"
		server_key = "SB-Mid-server-test456"

		signature_string = f"{order_id}{status_code}{gross_amount}{server_key}"
		valid_signature = hashlib.sha512(signature_string.encode()).hexdigest()

		# Test valid signature
		self.assertTrue(
			validate_midtrans_signature(
				order_id=order_id,
				status_code=status_code,
				gross_amount=gross_amount,
				server_key=server_key,
				signature_key=valid_signature,
			)
		)

		# Test invalid signature
		self.assertFalse(
			validate_midtrans_signature(
				order_id=order_id,
				status_code=status_code,
				gross_amount=gross_amount,
				server_key=server_key,
				signature_key="wrong_signature",
			)
		)


class TestMidtransSnapAPI(unittest.TestCase):
	"""Test cases for Midtrans Snap API client."""

	def test_sandbox_url_selection(self):
		"""Test that sandbox URL is selected when is_sandbox=True."""
		api = MidtransSnapAPI(server_key="test_key", is_sandbox=True)
		self.assertEqual(api.base_url, MIDTRANS_SANDBOX_SNAP_URL)

	def test_production_url_selection(self):
		"""Test that production URL is selected when is_sandbox=False."""
		api = MidtransSnapAPI(server_key="test_key", is_sandbox=False)
		self.assertEqual(api.base_url, MIDTRANS_PRODUCTION_SNAP_URL)

	def test_auth_header_generation(self):
		"""Test that authorization header is correctly generated."""
		import base64

		server_key = "SB-Mid-server-test123"
		api = MidtransSnapAPI(server_key=server_key, is_sandbox=True)

		expected_auth = f"Basic {base64.b64encode(f'{server_key}:'.encode()).decode()}"
		self.assertEqual(api._get_auth_header(), expected_auth)

	def test_headers_structure(self):
		"""Test that request headers have correct structure."""
		api = MidtransSnapAPI(server_key="test_key", is_sandbox=True)
		headers = api._get_headers()

		self.assertIn("Content-Type", headers)
		self.assertIn("Accept", headers)
		self.assertIn("Authorization", headers)
		self.assertEqual(headers["Content-Type"], "application/json")
		self.assertEqual(headers["Accept"], "application/json")


class TestMidtransConstants(unittest.TestCase):
	"""Test cases for Midtrans constants."""

	def test_sandbox_url(self):
		"""Test sandbox URL is correct."""
		self.assertEqual(
			MIDTRANS_SANDBOX_SNAP_URL,
			"https://app.sandbox.midtrans.com/snap/v1/transactions",
		)

	def test_production_url(self):
		"""Test production URL is correct."""
		self.assertEqual(
			MIDTRANS_PRODUCTION_SNAP_URL,
			"https://app.midtrans.com/snap/v1/transactions",
		)

	def test_successful_statuses(self):
		"""Test successful statuses include expected values."""
		self.assertIn("capture", SUCCESSFUL_STATUSES)
		self.assertIn("settlement", SUCCESSFUL_STATUSES)

	def test_failed_statuses(self):
		"""Test failed statuses include expected values."""
		self.assertIn("deny", FAILED_STATUSES)
		self.assertIn("cancel", FAILED_STATUSES)
		self.assertIn("expire", FAILED_STATUSES)

	def test_settlement_status(self):
		"""Test settlement status constant."""
		self.assertEqual(TRANSACTION_STATUS_SETTLEMENT, "settlement")

	def test_supported_currencies_not_empty(self):
		"""Test that supported currencies list is not empty."""
		self.assertTrue(len(SUPPORTED_CURRENCIES) > 0)
		self.assertIn("IDR", SUPPORTED_CURRENCIES)
