# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import hashlib

import frappe


class MidtransSignatureValidator:
	"""Validator for Midtrans webhook signature verification."""

	def __init__(
		self,
		order_id: str,
		status_code: str,
		gross_amount: str,
		server_key: str,
		signature_key: str,
	):
		"""
		Initialize signature validator.

		Args:
		    order_id: Order ID from callback
		    status_code: Status code from callback
		    gross_amount: Gross amount from callback
		    server_key: Server key from Midtrans Settings
		    signature_key: Signature key from callback to verify
		"""
		self.order_id = order_id
		self.status_code = status_code
		self.gross_amount = gross_amount
		self.server_key = server_key
		self.signature_key = signature_key

	def _generate_signature(self) -> str:
		"""
		Generate SHA512 signature hash.

		Midtrans signature formula:
		SHA512(order_id + status_code + gross_amount + server_key)
		"""
		signature_string = f"{self.order_id}{self.status_code}{self.gross_amount}{self.server_key}"
		return hashlib.sha512(signature_string.encode()).hexdigest()

	@property
	def is_valid(self) -> bool:
		"""Check if the provided signature is valid."""
		generated_signature = self._generate_signature()
		return generated_signature == self.signature_key

	def validate(self) -> None:
		"""Validate signature and raise error if invalid."""
		if not self.is_valid:
			frappe.log_error(
				message=f"Invalid Midtrans signature for order: {self.order_id}",
				title="Midtrans Signature Validation Failed",
			)
			frappe.throw(
				frappe._("Invalid signature - request may have been tampered with"),
				frappe.PermissionError,
			)


def validate_midtrans_signature(
	order_id: str,
	status_code: str,
	gross_amount: str,
	server_key: str,
	signature_key: str,
) -> bool:
	"""
	Convenience function to validate Midtrans signature.

	Args:
	    order_id: Order ID from callback
	    status_code: Status code from callback
	    gross_amount: Gross amount from callback
	    server_key: Server key from Midtrans Settings
	    signature_key: Signature key from callback

	Returns:
	    bool: True if signature is valid
	"""
	validator = MidtransSignatureValidator(
		order_id=order_id,
		status_code=status_code,
		gross_amount=gross_amount,
		server_key=server_key,
		signature_key=signature_key,
	)
	return validator.is_valid
