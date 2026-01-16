import frappe


def execute():
	"""
	Fix Payment Gateway records for Single DocType payment gateways.

	Single DocTypes cannot be used as Dynamic Link targets.
	This patch ensures gateway_settings and gateway_controller are NULL
	for all Single DocType payment gateways.
	"""
	single_doctype_gateways = [
		"Midtrans",
		"Xendit",
		"Razorpay",
		"PayPal",
		"Paymob",
		"PayTM",
		"Braintree",
		"M-Pesa",
	]

	for gateway_name in single_doctype_gateways:
		if frappe.db.exists("Payment Gateway", gateway_name):
			# Use direct SQL update to avoid any validation issues
			frappe.db.sql(
				"""
				UPDATE `tabPayment Gateway`
				SET gateway_settings = NULL, gateway_controller = NULL
				WHERE gateway = %s
				""",
				gateway_name,
			)

	frappe.db.commit()
