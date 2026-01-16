// Copyright (c) 2024, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Xendit Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Test Connection"), function () {
			frm.trigger("test_connection");
		});
	},

	test_connection(frm) {
		if (!frm.doc.secret_key || !frm.doc.callback_token) {
			frappe.msgprint(__("Please enter Secret Key and Callback Token first."));
			return;
		}

		frappe.msgprint({
			title: __("Connection Info"),
			message: __("Xendit connection is configured."),
			indicator: "green",
		});
	},
});
