# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import hashlib
import unittest

from frappe.tests.utils import FrappeTestCase

from payments.payment_gateways.midtrans.constants import (
	MIDTRANS_PRODUCTION_SNAP_URL,
	MIDTRANS_SANDBOX_SNAP_URL,
	SUCCESSFUL_STATUSES,
	TRANSACTION_STATUS_SETTLEMENT,
)
from payments.payment_gateways.midtrans.signature_validator import (
	MidtransSignatureValidator,
	validate_midtrans_signature,
)


class TestMidtransSettings(FrappeTestCase):
	"""Test cases for Midtrans Settings DocType."""

	pass


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

	def test_settlement_status(self):
		"""Test settlement status constant."""
		self.assertEqual(TRANSACTION_STATUS_SETTLEMENT, "settlement")
