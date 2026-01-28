# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# License: MIT. See LICENSE

import frappe
from frappe import _
from frappe.model.document import Document


class PaymentGateway(Document):
	"""
	Payment Gateway configuration for integrating payment providers.
	
	Manages the connection between payment methods and their settings,
	allowing dynamic linking to various payment gateway configurations.
	"""

	def validate(self):
		"""Validate that Single DocTypes are not used as gateway_settings."""
		if self.gateway_settings:
			# Check if the gateway_settings is a Single DocType
			meta = frappe.get_meta(self.gateway_settings)
			if meta.is_single:
				# Single DocTypes cannot be used as Dynamic Link targets
				# For Single DocType payment gateways, gateway_settings and gateway_controller should be None
				# The system will automatically fallback to using "{gateway_name} Settings" pattern
				frappe.throw(
					_(
						"{0} is a Single DocType and cannot be used as a Dynamic Link target. "
						"Please leave Gateway Settings and Gateway Controller fields empty. "
						"The system will automatically use the '{1} Settings' pattern."
					).format(self.gateway_settings, self.gateway or "")
				)
