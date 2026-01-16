# **Technical Design Document: Integrasi Payment Gateway Indonesia (Midtrans & Xendit)**

Target App: payments (Forked from frappe/payments)  
Framework: Frappe Framework v16 (Python 3.10+)  
Scope: Integrasi Midtrans Snap & Xendit Invoice ke dalam ekosistem ERPNext.

## **1\. Arsitektur & Struktur Folder**

Aplikasi payments harus dimodifikasi dengan menambahkan struktur berikut. Jangan mengubah file inti yang sudah ada kecuali diperlukan.

### **Struktur Direktori Baru**

apps/payments/payments/  
├── payment\_gateways/  
│   ├── doctype/  
│   │   ├── midtrans\_settings/         \<-- NEW  
│   │   │   ├── midtrans\_settings.json  
│   │   │   ├── midtrans\_settings.py  
│   │   │   └── midtrans\_settings.js  
│   │   ├── xendit\_settings/           \<-- NEW  
│   │   │   ├── xendit\_settings.json  
│   │   │   ├── xendit\_settings.py  
│   │   │   └── xendit\_settings.js  
├── utils/  
│   └── indonesia\_payment\_handler.py   \<-- NEW (Logika Webhook/Callback)

## **2\. Spesifikasi DocType (Configuration)**

### **A. Midtrans Settings**

Path: payments/payment\_gateways/doctype/midtrans\_settings/midtrans\_settings.json  
Type: Single DocType  
Fields:

1. gateway\_name (Data, Read Only): Default "Midtrans"  
2. server\_key (Password): API Key Server dari Midtrans Dashboard.  
3. client\_key (Data): API Key Client (untuk frontend JS jika perlu).  
4. is\_sandbox (Check): Jika True, gunakan URL Sandbox. Jika False, gunakan Production.  
5. payment\_account (Link \- Account): Akun Bank/GL untuk menampung pembayaran masuk.

### **B. Xendit Settings**

Path: payments/payment\_gateways/doctype/xendit\_settings/xendit\_settings.json  
Type: Single DocType  
Fields:

1. gateway\_name (Data, Read Only): Default "Xendit"  
2. secret\_key (Password): Secret Key dari Xendit Dashboard.  
3. callback\_token (Password): Token verifikasi untuk Webhook.  
4. payment\_account (Link \- Account): Akun Bank/GL.

## **3\. Implementasi Controller (Python Logic)**

Setiap class Settings harus mewarisi PaymentGatewaySettings agar dikenali oleh ERPNext.

### **A. Midtrans Logic (midtrans\_settings.py)**

**Class:** MidtransSettings(PaymentGatewaySettings)

**Method:** get\_payment\_url(self, \*\*kwargs)

* **Context:** Dipanggil saat user klik "Pay" di Payment Request/Invoice.  
* **Input (kwargs):**  
  * amount (Float)  
  * reference\_doctype (String)  
  * reference\_docname (String)  
  * payer\_email (String)  
  * payer\_name (String)  
* **Logic Steps:**  
  1. Ambil server\_key menggunakan self.get\_password("server\_key").  
  2. Tentukan Base URL:  
     * Sandbox: https://app.sandbox.midtrans.com/snap/v1/transactions  
     * Prod: https://app.midtrans.com/snap/v1/transactions  
  3. Generate Auth Header: Base64(server\_key \+ ":").  
  4. Construct Payload:  
     * transaction\_details.order\_id: Gabungan {reference\_doctype}-{reference\_docname} (Contoh: "Sales Invoice-INV-2024-001").  
     * transaction\_details.gross\_amount: **PENTING:** Harus di-cast ke int() (Midtrans menolak desimal).  
     * credit\_card.secure: True.  
  5. Send POST Request ke Midtrans.  
  6. **Return:** redirect\_url dari respon JSON Midtrans.

### **B. Xendit Logic (xendit\_settings.py)**

**Class:** XenditSettings(PaymentGatewaySettings)

**Method:** get\_payment\_url(self, \*\*kwargs)

* **Logic Steps:**  
  1. Ambil secret\_key.  
  2. Base URL: https://api.xendit.co/v2/invoices.  
  3. Generate Auth Header: Base64(secret\_key \+ ":").  
  4. Construct Payload:  
     * external\_id: {reference\_doctype}-{reference\_docname}.  
     * amount: Float/Int (Xendit menerima desimal).  
     * payer\_email: Dari kwargs.  
     * description: "Payment for {reference\_docname}".  
  5. Send POST Request ke Xendit.  
  6. **Return:** invoice\_url dari respon JSON Xendit.

## **4\. Webhook / Callback Handler**

File ini menangani notifikasi HTTP POST dari server Midtrans/Xendit saat pembayaran sukses.

**Path:** payments/utils/indonesia\_payment\_handler.py

### **A. Endpoint Midtrans**

Decorator: @frappe.whitelist(allow\_guest=True)  
Function: midtrans\_callback(\*\*kwargs)  
**Logic:**

1. Ambil JSON data: data \= frappe.request.get\_json().  
2. **Security Check (Wajib):**  
   * Ambil signature\_key dari JSON.  
   * Ambil status\_code, gross\_amount, order\_id dari JSON.  
   * Ambil server\_key dari DocType Midtrans Settings.  
   * Generate Hash SHA512: order\_id \+ status\_code \+ gross\_amount \+ server\_key.  
   * Compare hash lokal dengan signature\_key dari request. Jika beda \-\> Raise frappe.PermissionError.  
3. **Status Handling:**  
   * Jika transaction\_status \== capture ATAU settlement:  
     * Panggil fungsi finalize\_payment(order\_id).  
   * Jika deny, cancel, expire:  
     * Update status Payment Request jadi "Failed" atau "Cancelled".

### **B. Endpoint Xendit**

Decorator: @frappe.whitelist(allow\_guest=True)  
Function: xendit\_callback(\*\*kwargs)  
**Logic:**

1. **Security Check:**  
   * Ambil Header x-callback-token dari request.  
   * Ambil token dari DocType Xendit Settings.  
   * Jika tidak sama \-\> Raise frappe.PermissionError.  
2. **Status Handling:**  
   * Ambil external\_id dan status.  
   * Jika status \== PAID:  
     * Panggil fungsi finalize\_payment(external\_id).

## **5\. Fungsi Core: Finalize Payment**

Fungsi ini bertugas membuat catatan akuntansi (Jurnal) di ERPNext secara otomatis.

**Function:** finalize\_payment(order\_ref)

**Logic:**

1. Parse order\_ref (misal: "Sales Invoice-INV-001") untuk mendapatkan DocType dan DocName, ATAU cari dokumen Payment Request yang memiliki field reference tersebut.  
2. Ambil dokumen Payment Request yang statusnya masih 'Pending'.  
3. Gunakan API bawaan Frappe untuk membuat Payment Entry:  
   from erpnext.accounts.doctype.payment\_request.payment\_request import make\_payment\_entry

   pr \= frappe.get\_doc("Payment Request", request\_name)  
   pe \= make\_payment\_entry(request\_name)  
   pe.reference\_no \= order\_ref  
   pe.reference\_date \= nowdate()  
   pe.save(ignore\_permissions=True)  
   pe.submit()

4. Update status Payment Request menjadi 'Paid'.  
5. Commit database: frappe.db.commit().

## **6\. Daftar Library yang Dibutuhkan**

Pastikan library ini ada di file requirements.txt aplikasi payments atau sudah terinstall di env:

requests  
hashlib  (Standard Lib)  
hmac     (Standard Lib)  
base64   (Standard Lib)  
json     (Standard Lib)

## **7\. Referensi API**

* **Midtrans Snap Docs:** https://www.google.com/search?q=https://docs.midtrans.com/reference/snap-transactions  
* **Xendit Invoice Docs:** https://www.google.com/search?q=https://developers.xendit.co/api-reference/invoices/create-invoice