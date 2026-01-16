# Payments

A payments app for Frappe Framework with support for multiple payment gateways including Indonesian payment gateways (Midtrans & Xendit).

## Supported Payment Gateways

| Gateway | Region | Payment Methods |
|---------|--------|-----------------|
| **Midtrans** | Indonesia | Credit Card, Bank Transfer, E-Wallet (GoPay, OVO, DANA), QRIS, Convenience Store |
| **Xendit** | Indonesia, Philippines | Credit Card, Bank Transfer, E-Wallet, QRIS, Retail Outlets |
| Razorpay | India | Credit Card, Debit Card, UPI, Netbanking, Wallets |
| Stripe | Global | Credit Card, Apple Pay, Google Pay |
| PayPal | Global | PayPal Balance, Credit Card |
| Paymob | Egypt, Pakistan | Credit Card, Mobile Wallets |
| Braintree | Global | Credit Card, PayPal, Venmo |
| GoCardless | Europe, UK | Direct Debit |
| PayTM | India | UPI, Wallet, Cards |
| M-Pesa | Kenya | Mobile Money |

---

## Installation

### Prerequisites
- Frappe Framework v16+
- ERPNext (optional, for Payment Entry creation)
- Python 3.10+

### Steps

1. **Install Frappe & Bench**
   ```bash
   # Follow official guide: https://frappeframework.com/docs/user/en/installation
   ```

2. **Get the Payments App**
   ```bash
   bench get-app https://github.com/andrimuhyidin/payments.git
   # Or specify branch
   bench get-app https://github.com/andrimuhyidin/payments.git --branch develop
   ```

3. **Install on Your Site**
   ```bash
   bench --site <your-site> install-app payments
   ```

4. **Run Migrations**
   ```bash
   bench --site <your-site> migrate
   ```

---

## Indonesian Payment Gateways Setup

### Midtrans Setup

Midtrans is one of the leading payment gateways in Indonesia, supporting various payment methods including credit cards, bank transfers, e-wallets, and QRIS.

#### Step 1: Create Midtrans Account

1. Go to [Midtrans Dashboard](https://dashboard.midtrans.com)
2. Register for a new account or login
3. Complete the account verification process

#### Step 2: Get API Keys

1. Login to Midtrans Dashboard
2. Go to **Settings > Access Keys**
3. Copy the following:
   - **Server Key** (keep this secret!)
   - **Client Key**
   - **Merchant ID**

> **Note:** Use Sandbox keys for testing, Production keys for live transactions.

#### Step 3: Configure in Frappe

1. Go to **Midtrans Settings** (`/app/midtrans-settings`)
2. Fill in the configuration:

| Field | Description |
|-------|-------------|
| Server Key | Your Midtrans Server Key (from dashboard) |
| Client Key | Your Midtrans Client Key (from dashboard) |
| Merchant ID | Your Merchant ID (optional) |
| Is Sandbox | ✓ Enable for testing, disable for production |
| Payment Account | Select the GL Account for receiving payments |
| Redirect To | URL to redirect after successful payment |

3. Click **Save**

#### Step 4: Configure Webhook (Notification URL)

1. Go to Midtrans Dashboard > **Settings > Configuration**
2. Set **Payment Notification URL** to:
   ```
   https://your-site.com/api/method/payments.utils.indonesia_payment_handler.midtrans_callback
   ```
3. Enable notification for these events:
   - ✓ Pay
   - ✓ Recurring
   - ✓ Refund

#### Step 5: Test the Integration

1. Create a **Payment Request** in ERPNext
2. Select **Midtrans** as the Payment Gateway
3. Click **Create Payment URL**
4. Complete the payment using Midtrans test credentials:
   - Card Number: `4811 1111 1111 1114`
   - CVV: `123`
   - Exp: Any future date

---

### Xendit Setup

Xendit is a payment gateway supporting Indonesia and Philippines with various payment methods including bank transfers, e-wallets, and retail outlets.

#### Step 1: Create Xendit Account

1. Go to [Xendit Dashboard](https://dashboard.xendit.co)
2. Register for a new account
3. Complete the account verification

#### Step 2: Get API Keys

1. Login to Xendit Dashboard
2. Go to **Settings > API Keys**
3. Generate or copy:
   - **Secret Key** (keep this secret!)
4. Go to **Settings > Webhooks**
5. Copy the **Verification Token** (Callback Token)

#### Step 3: Configure in Frappe

1. Go to **Xendit Settings** (`/app/xendit-settings`)
2. Fill in the configuration:

| Field | Description |
|-------|-------------|
| Secret Key | Your Xendit Secret Key |
| Callback Token | Webhook Verification Token from Xendit Dashboard |
| Payment Account | Select the GL Account for receiving payments |
| Redirect To | URL to redirect after successful payment |
| Invoice Duration | Invoice expiry in seconds (default: 86400 = 24 hours) |

3. Click **Save**

#### Step 4: Configure Webhook

1. Go to Xendit Dashboard > **Settings > Webhooks**
2. Add a new webhook with URL:
   ```
   https://your-site.com/api/method/payments.utils.indonesia_payment_handler.xendit_callback
   ```
3. Select events to subscribe:
   - ✓ `invoices.paid`
   - ✓ `invoices.expired`

#### Step 5: Test the Integration

1. Create a **Payment Request** in ERPNext
2. Select **Xendit** as the Payment Gateway
3. Click **Create Payment URL**
4. Use Xendit test mode to simulate payments

---

## Usage Guide

### Creating Payment Request

1. **From Sales Invoice:**
   - Open a submitted Sales Invoice
   - Click **Create > Payment Request**
   - Select your payment gateway (Midtrans/Xendit)
   - Set the email recipient
   - Submit the Payment Request

2. **From Web Form:**
   - Edit your Web Form
   - Go to **Payments** tab
   - Enable **Accept Payment**
   - Select your Payment Gateway
   - Configure amount and currency

### Payment Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Payment Request │────▶│  Payment Gateway │────▶│ Customer Pays   │
│    Created      │     │  (Midtrans/Xendit)│     │                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
┌─────────────────┐     ┌──────────────────┐              │
│ Payment Entry   │◀────│ Webhook Callback │◀─────────────┘
│   Created       │     │    Received      │
└─────────────────┘     └──────────────────┘
```

### Webhook Endpoints

| Gateway | Webhook URL |
|---------|-------------|
| Midtrans | `/api/method/payments.utils.indonesia_payment_handler.midtrans_callback` |
| Xendit | `/api/method/payments.utils.indonesia_payment_handler.xendit_callback` |

---

## API Reference

### Get Payment URL Programmatically

```python
import frappe

# For Midtrans
midtrans_settings = frappe.get_doc("Midtrans Settings")
payment_url = midtrans_settings.get_payment_url(
    amount=100000,
    reference_doctype="Sales Invoice",
    reference_docname="INV-2024-00001",
    payer_email="customer@example.com",
    payer_name="John Doe",
    currency="IDR"
)

# For Xendit
xendit_settings = frappe.get_doc("Xendit Settings")
payment_url = xendit_settings.get_payment_url(
    amount=100000,
    reference_doctype="Sales Invoice",
    reference_docname="INV-2024-00001",
    payer_email="customer@example.com",
    payer_name="John Doe",
    description="Payment for Invoice INV-2024-00001",
    currency="IDR"
)
```

### Check Payment Status

```python
from payments.utils.indonesia_payment_handler import get_payment_status

# Check Midtrans transaction
status = get_payment_status(
    gateway="Midtrans",
    order_id="Sales Invoice-INV-2024-00001-IR-00001"
)

# Check Xendit invoice
status = get_payment_status(
    gateway="Xendit",
    order_id="invoice-id-from-xendit"
)
```

---

## Troubleshooting

### Common Issues

#### 1. Payment URL Not Generated

**Symptoms:** Error when clicking "Create Payment URL"

**Solutions:**
- Check if Server Key / Secret Key is correct
- Verify the Payment Gateway record exists
- Check Error Log for detailed error messages

```bash
bench --site <site> console
>>> frappe.get_last_doc("Error Log")
```

#### 2. Webhook Not Received

**Symptoms:** Payment completed but Payment Entry not created

**Solutions:**
- Verify webhook URL is accessible from internet
- Check if SSL certificate is valid
- Verify callback token (Xendit) or signature (Midtrans)
- Check Integration Request for webhook logs:
  ```
  /app/integration-request?integration_request_service=Midtrans
  ```

#### 3. Invalid Signature Error (Midtrans)

**Symptoms:** Webhook returns "Invalid signature" error

**Solutions:**
- Verify Server Key matches between dashboard and settings
- Check if you're using Sandbox key with Sandbox mode enabled
- Ensure webhook is receiving correct data format

#### 4. Invalid Callback Token Error (Xendit)

**Symptoms:** Webhook returns "Invalid callback token" error

**Solutions:**
- Copy the exact Verification Token from Xendit Dashboard
- Check for extra spaces in the token
- Regenerate the token if needed

### Debug Mode

Enable debug logging for payment gateways:

```python
# In site_config.json
{
    "developer_mode": 1,
    "logging": 1
}
```

Check logs:
```bash
tail -f ~/frappe-bench/logs/frappe.log | grep -i "midtrans\|xendit"
```

---

## Security Best Practices

1. **Never expose Server Keys / Secret Keys** in client-side code
2. **Always validate webhooks** using signature (Midtrans) or callback token (Xendit)
3. **Use HTTPS** for webhook endpoints
4. **Regularly rotate** API keys
5. **Monitor Integration Requests** for suspicious activities

---

## App Structure

```
payments/
├── payments/                    # Payments module (Payment Gateway DocType)
├── payment_gateways/           # Payment Gateways module
│   ├── doctype/
│   │   ├── midtrans_settings/  # Midtrans configuration
│   │   ├── xendit_settings/    # Xendit configuration
│   │   ├── razorpay_settings/
│   │   ├── stripe_settings/
│   │   └── ...
│   ├── midtrans/               # Midtrans helper modules
│   │   ├── constants.py
│   │   ├── snap_api.py
│   │   └── signature_validator.py
│   └── xendit/                 # Xendit helper modules
│       ├── constants.py
│       ├── invoice_api.py
│       └── callback_validator.py
├── utils/
│   ├── utils.py
│   └── indonesia_payment_handler.py  # Webhook handlers
├── templates/                  # Checkout page templates
└── overrides/                  # Frappe overrides
```

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `bench --site <site> run-tests --app payments`
5. Submit a Pull Request

---

## License

MIT License - see [license.txt](license.txt)

---

## Support

- **Issues:** [GitHub Issues](https://github.com/andrimuhyidin/payments/issues)
- **Documentation:** [Frappe Framework Docs](https://frappeframework.com/docs)
- **Midtrans Docs:** [Midtrans Technical Documentation](https://docs.midtrans.com)
- **Xendit Docs:** [Xendit API Reference](https://developers.xendit.co)
