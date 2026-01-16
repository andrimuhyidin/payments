# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe


class XenditCallbackValidator:
	"""Validator for Xendit webhook callback verification."""

	def __init__(self, callback_token: str, incoming_token: str):
		"""
		Initialize callback validator.

		Args:
		    callback_token: Callback token from Xendit Settings
		    incoming_token: Token from incoming webhook request header
		"""
		self.callback_token = callback_token
		self.incoming_token = incoming_token

	@property
	def is_valid(self) -> bool:
		"""Check if the incoming token matches the configured callback token."""
		if not self.callback_token or not self.incoming_token:
			return False
		return self.callback_token == self.incoming_token

	def validate(self) -> None:
		"""Validate callback token and raise error if invalid."""
		if not self.is_valid:
			frappe.log_error(
				message=f"Invalid Xendit callback token received",
				title="Xendit Callback Validation Failed",
			)
			frappe.throw(
				frappe._("Invalid callback token - unauthorized request"),
				frappe.PermissionError,
			)


def validate_xendit_callback(callback_token: str, incoming_token: str) -> bool:
	"""
	Convenience function to validate Xendit callback token.

	Args:
	    callback_token: Callback token from Xendit Settings
	    incoming_token: Token from incoming webhook request header

	Returns:
	    bool: True if token is valid
	"""
	validator = XenditCallbackValidator(
		callback_token=callback_token,
		incoming_token=incoming_token,
	)
	return validator.is_valid
