# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, flt
import json


class RefundRequest(Document):
	"""
	Refund Request DocType for processing payment refunds.
	
	Manages refund requests across multiple payment gateways,
	tracking status, amounts, and gateway responses.
	"""
	
	def validate(self):
		"""Validate refund request before saving."""
		self.validate_integration_request()
		self.validate_refund_amount()
		self.set_payment_gateway()
		self.set_original_amount()
		self.determine_refund_type()
	
	def validate_integration_request(self):
		"""Ensure integration request exists and is valid for refund."""
		if not self.integration_request:
			frappe.throw(_("Integration Request is required"))
		
		ir = frappe.get_doc("Integration Request", self.integration_request)
		
		# Check if payment was successful
		if ir.status not in ["Completed", "Authorized"]:
			frappe.throw(_("Can only refund completed or authorized payments"))
		
		# Check if already fully refunded
		existing_refunds = frappe.get_all(
			"Refund Request",
			filters={
				"integration_request": self.integration_request,
				"status": ["in", ["Completed", "Processing", "Pending"]],
				"name": ["!=", self.name or ""]
			},
			fields=["sum(refund_amount) as total_refunded"]
		)
		
		total_refunded = flt(existing_refunds[0].total_refunded) if existing_refunds else 0
		original_amount = self.get_original_amount_from_ir(ir)
		
		if total_refunded >= original_amount:
			frappe.throw(_("This payment has already been fully refunded"))
	
	def validate_refund_amount(self):
		"""Validate refund amount is within bounds."""
		if not self.refund_amount or flt(self.refund_amount) <= 0:
			frappe.throw(_("Refund amount must be greater than zero"))
		
		ir = frappe.get_doc("Integration Request", self.integration_request)
		original_amount = self.get_original_amount_from_ir(ir)
		
		# Get total already refunded
		existing_refunds = frappe.get_all(
			"Refund Request",
			filters={
				"integration_request": self.integration_request,
				"status": ["in", ["Completed", "Processing", "Pending"]],
				"name": ["!=", self.name or ""]
			},
			fields=["sum(refund_amount) as total_refunded"]
		)
		
		total_refunded = flt(existing_refunds[0].total_refunded) if existing_refunds else 0
		available_for_refund = original_amount - total_refunded
		
		if flt(self.refund_amount) > available_for_refund:
			frappe.throw(
				_("Refund amount ({0}) exceeds available amount for refund ({1})").format(
					self.refund_amount, available_for_refund
				)
			)
	
	def set_payment_gateway(self):
		"""Set payment gateway from integration request."""
		if not self.payment_gateway and self.integration_request:
			ir = frappe.get_doc("Integration Request", self.integration_request)
			service = ir.integration_request_service
			
			if frappe.db.exists("Payment Gateway", service):
				self.payment_gateway = service
	
	def set_original_amount(self):
		"""Set original amount from integration request."""
		if self.integration_request:
			ir = frappe.get_doc("Integration Request", self.integration_request)
			self.original_amount = self.get_original_amount_from_ir(ir)
			
			# Try to get currency
			try:
				data = json.loads(ir.data or "{}")
				self.original_currency = data.get("currency", "IDR")
			except (json.JSONDecodeError, TypeError):
				self.original_currency = "IDR"
	
	def determine_refund_type(self):
		"""Determine if refund is full or partial."""
		if flt(self.refund_amount) >= flt(self.original_amount):
			self.refund_type = "Full"
		else:
			self.refund_type = "Partial"
	
	def get_original_amount_from_ir(self, ir):
		"""Extract original payment amount from integration request."""
		try:
			data = json.loads(ir.data or "{}")
			return flt(data.get("amount", 0))
		except (json.JSONDecodeError, TypeError):
			return 0
	
	def on_submit(self):
		"""Process refund when submitted."""
		self.status = "Pending"
		self.db_set("status", "Pending")
		
		# Enqueue refund processing
		frappe.enqueue(
			"payments.refund.processor.process_refund",
			refund_request=self.name,
			queue="short",
			timeout=300
		)
		
		frappe.msgprint(
			_("Refund request submitted. Processing will begin shortly."),
			indicator="blue"
		)
	
	def on_cancel(self):
		"""Handle refund cancellation."""
		if self.status in ["Completed"]:
			frappe.throw(_("Cannot cancel a completed refund"))
		
		self.status = "Cancelled"
		self.db_set("status", "Cancelled")
	
	def update_status(self, status, gateway_refund_id=None, gateway_response=None, error_message=None):
		"""Update refund status with gateway response."""
		self.status = status
		
		if gateway_refund_id:
			self.gateway_refund_id = gateway_refund_id
		
		if gateway_response:
			self.gateway_response = json.dumps(gateway_response, indent=2)
		
		if error_message:
			self.error_message = error_message
		
		if status == "Completed":
			self.processed_at = now_datetime()
		
		self.save(ignore_permissions=True)
