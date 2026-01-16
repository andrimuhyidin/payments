# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

# Xendit API URLs
XENDIT_API_BASE_URL = "https://api.xendit.co"
XENDIT_INVOICE_URL = f"{XENDIT_API_BASE_URL}/v2/invoices"

# Invoice status constants
INVOICE_STATUS_PENDING = "PENDING"
INVOICE_STATUS_PAID = "PAID"
INVOICE_STATUS_SETTLED = "SETTLED"
INVOICE_STATUS_EXPIRED = "EXPIRED"

# Callback event types
CALLBACK_EVENT_INVOICE_PAID = "invoices.paid"
CALLBACK_EVENT_INVOICE_EXPIRED = "invoices.expired"

# Successful statuses
SUCCESSFUL_STATUSES = [INVOICE_STATUS_PAID, INVOICE_STATUS_SETTLED]
FAILED_STATUSES = [INVOICE_STATUS_EXPIRED]

# Supported currencies
SUPPORTED_CURRENCIES = ["IDR", "PHP", "USD"]

# Default invoice duration (24 hours in seconds)
DEFAULT_INVOICE_DURATION = 86400

# Available payment methods
PAYMENT_METHODS = [
	"BCA",
	"BNI",
	"BRI",
	"MANDIRI",
	"PERMATA",
	"BSI",
	"BJB",
	"SAHABAT_SAMPOERNA",
	"CIMB",
	"OVO",
	"DANA",
	"SHOPEEPAY",
	"LINKAJA",
	"QRIS",
	"ALFAMART",
	"INDOMARET",
	"CREDIT_CARD",
]
