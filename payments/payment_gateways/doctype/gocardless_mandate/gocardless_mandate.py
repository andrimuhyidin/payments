# Copyright (c) 2018, Frappe Technologies and contributors
# For license information, please see license.txt


from frappe.model.document import Document


class GoCardlessMandate(Document):
	"""
	GoCardless Mandate for storing customer direct debit authorization.
	
	Represents a customer's authorization for GoCardless to collect
	payments from their bank account via Direct Debit scheme.
	"""

	pass
