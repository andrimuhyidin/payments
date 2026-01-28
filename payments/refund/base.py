# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""
Base class for payment gateway refund handlers.

Each payment gateway should implement its own refund handler
by extending this base class.
"""

import frappe
from frappe import _
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import json


class RefundHandler(ABC):
	"""
	Abstract base class for payment gateway refund handlers.
	
	Subclasses must implement:
	- validate(): Validate refund can be processed
	- process(): Execute refund with gateway
	- handle_webhook(): Handle refund webhook callbacks
	"""
	
	def __init__(self, refund_request_name: str):
		"""
		Initialize refund handler with a refund request.
		
		Args:
			refund_request_name: Name of the Refund Request document
		"""
		self.refund_request = frappe.get_doc("Refund Request", refund_request_name)
		self.integration_request = frappe.get_doc(
			"Integration Request", 
			self.refund_request.integration_request
		)
		self.gateway_settings = self._get_gateway_settings()
		self.payment_data = self._parse_payment_data()
	
	def _get_gateway_settings(self) -> Optional[Any]:
		"""Get gateway settings document."""
		gateway = self.refund_request.payment_gateway
		if not gateway:
			return None
		
		try:
			# Try to get gateway-specific settings
			settings_doctype = f"{gateway} Settings"
			if frappe.db.exists("DocType", settings_doctype):
				return frappe.get_single(settings_doctype)
		except Exception:
			pass
		
		return None
	
	def _parse_payment_data(self) -> Dict[str, Any]:
		"""Parse payment data from integration request."""
		try:
			return json.loads(self.integration_request.data or "{}")
		except (json.JSONDecodeError, TypeError):
			return {}
	
	@abstractmethod
	def validate(self) -> bool:
		"""
		Validate that refund can be processed.
		
		Returns:
			True if refund can proceed, False otherwise
			
		Raises:
			frappe.ValidationError: If validation fails
		"""
		pass
	
	@abstractmethod
	def process(self) -> Dict[str, Any]:
		"""
		Process refund with payment gateway.
		
		Returns:
			Dictionary with:
			- success: bool
			- refund_id: str (gateway refund ID)
			- message: str
			- data: dict (full gateway response)
			
		Raises:
			Exception: If refund processing fails
		"""
		pass
	
	@abstractmethod
	def handle_webhook(self, payload: Dict[str, Any]) -> None:
		"""
		Handle refund webhook from payment gateway.
		
		Args:
			payload: Webhook payload from gateway
		"""
		pass
	
	def get_transaction_id(self) -> Optional[str]:
		"""Get original transaction ID from payment data."""
		# Common field names for transaction ID
		for field in ["transaction_id", "order_id", "payment_id", "id"]:
			if field in self.payment_data:
				return self.payment_data[field]
		return None
	
	def update_refund_status(
		self, 
		status: str, 
		refund_id: Optional[str] = None,
		response: Optional[Dict] = None,
		error: Optional[str] = None
	):
		"""
		Update refund request status.
		
		Args:
			status: New status (Processing, Completed, Failed)
			refund_id: Gateway refund ID
			response: Full gateway response
			error: Error message if failed
		"""
		self.refund_request.update_status(
			status=status,
			gateway_refund_id=refund_id,
			gateway_response=response,
			error_message=error
		)
	
	def log_error(self, message: str, title: str = "Refund Error"):
		"""Log error for debugging."""
		frappe.log_error(
			message=message,
			title=f"{title} - {self.refund_request.name}"
		)


class GenericRefundHandler(RefundHandler):
	"""
	Generic refund handler for gateways without specific implementation.
	
	This handler marks refunds as requiring manual processing.
	"""
	
	def validate(self) -> bool:
		"""Generic validation always passes."""
		return True
	
	def process(self) -> Dict[str, Any]:
		"""Mark refund as requiring manual processing."""
		frappe.msgprint(
			_("This payment gateway does not support automated refunds. "
			  "Please process the refund manually in the gateway dashboard."),
			indicator="orange",
			title=_("Manual Processing Required")
		)
		
		return {
			"success": False,
			"refund_id": None,
			"message": "Manual processing required",
			"data": {"manual_processing": True}
		}
	
	def handle_webhook(self, payload: Dict[str, Any]) -> None:
		"""No webhook handling for generic handler."""
		pass
