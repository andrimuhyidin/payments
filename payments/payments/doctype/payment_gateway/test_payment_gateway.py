# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: MIT. See LICENSE
import unittest

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPaymentGateway(FrappeTestCase):
	"""Test cases for Payment Gateway DocType."""

	def setUp(self):
		"""Set up test fixtures."""
		# Clean up any test payment gateways from previous runs
		for name in frappe.get_all(
			"Payment Gateway",
			filters={"gateway": ["like", "Test Gateway%"]},
			pluck="name"
		):
			frappe.delete_doc("Payment Gateway", name, force=True)

	def tearDown(self):
		"""Clean up after tests."""
		for name in frappe.get_all(
			"Payment Gateway",
			filters={"gateway": ["like", "Test Gateway%"]},
			pluck="name"
		):
			frappe.delete_doc("Payment Gateway", name, force=True)

	def test_create_payment_gateway(self):
		"""Test creating a basic payment gateway."""
		gateway = frappe.get_doc({
			"doctype": "Payment Gateway",
			"gateway": "Test Gateway Basic"
		})
		gateway.insert()

		self.assertEqual(gateway.gateway, "Test Gateway Basic")
		self.assertTrue(frappe.db.exists("Payment Gateway", gateway.name))

	def test_payment_gateway_with_settings(self):
		"""Test creating payment gateway with gateway settings."""
		gateway = frappe.get_doc({
			"doctype": "Payment Gateway",
			"gateway": "Test Gateway With Settings",
			"gateway_settings": None,  # No settings for basic test
			"gateway_controller": None
		})
		gateway.insert()

		self.assertTrue(frappe.db.exists("Payment Gateway", gateway.name))

	def test_validate_single_doctype_gateway_settings(self):
		"""Test that Single DocTypes cannot be used as gateway_settings."""
		# Create a payment gateway with a Single DocType as gateway_settings
		gateway = frappe.get_doc({
			"doctype": "Payment Gateway",
			"gateway": "Test Gateway Single",
			"gateway_settings": "Website Settings"  # This is a Single DocType
		})

		# Should throw validation error
		with self.assertRaises(frappe.ValidationError):
			gateway.insert()

	def test_payment_gateway_duplicate_name(self):
		"""Test that duplicate gateway names are not allowed."""
		gateway1 = frappe.get_doc({
			"doctype": "Payment Gateway",
			"gateway": "Test Gateway Duplicate"
		})
		gateway1.insert()

		gateway2 = frappe.get_doc({
			"doctype": "Payment Gateway",
			"gateway": "Test Gateway Duplicate"
		})

		# Should throw duplicate entry error
		with self.assertRaises(frappe.DuplicateEntryError):
			gateway2.insert()

	def test_payment_gateway_required_fields(self):
		"""Test that gateway field is required."""
		gateway = frappe.get_doc({
			"doctype": "Payment Gateway"
			# Missing required 'gateway' field
		})

		with self.assertRaises(frappe.MandatoryError):
			gateway.insert()


if __name__ == "__main__":
	unittest.main()
