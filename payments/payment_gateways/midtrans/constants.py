# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

# Midtrans API URLs
MIDTRANS_SANDBOX_SNAP_URL = "https://app.sandbox.midtrans.com/snap/v1/transactions"
MIDTRANS_PRODUCTION_SNAP_URL = "https://app.midtrans.com/snap/v1/transactions"

MIDTRANS_SANDBOX_API_URL = "https://api.sandbox.midtrans.com/v2"
MIDTRANS_PRODUCTION_API_URL = "https://api.midtrans.com/v2"

# Midtrans Snap Redirect URLs
MIDTRANS_SANDBOX_SNAP_REDIRECT = "https://app.sandbox.midtrans.com/snap/v2/vtweb"
MIDTRANS_PRODUCTION_SNAP_REDIRECT = "https://app.midtrans.com/snap/v2/vtweb"

# Transaction status constants
TRANSACTION_STATUS_CAPTURE = "capture"
TRANSACTION_STATUS_SETTLEMENT = "settlement"
TRANSACTION_STATUS_PENDING = "pending"
TRANSACTION_STATUS_DENY = "deny"
TRANSACTION_STATUS_CANCEL = "cancel"
TRANSACTION_STATUS_EXPIRE = "expire"
TRANSACTION_STATUS_REFUND = "refund"

# Fraud status constants
FRAUD_STATUS_ACCEPT = "accept"
FRAUD_STATUS_CHALLENGE = "challenge"
FRAUD_STATUS_DENY = "deny"

# Successful transaction statuses
SUCCESSFUL_STATUSES = [TRANSACTION_STATUS_CAPTURE, TRANSACTION_STATUS_SETTLEMENT]
FAILED_STATUSES = [TRANSACTION_STATUS_DENY, TRANSACTION_STATUS_CANCEL, TRANSACTION_STATUS_EXPIRE]

# Supported currencies (Midtrans primarily supports IDR)
SUPPORTED_CURRENCIES = ["IDR"]
