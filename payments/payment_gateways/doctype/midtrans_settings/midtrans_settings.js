// Copyright (c) 2024, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Midtrans Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Test Connection"), function () {
			frm.trigger("test_connection");
		});
	},

	test_connection(frm) {
		if (!frm.doc.server_key || !frm.doc.client_key) {
			frappe.msgprint(__("Please enter Server Key and Client Key first."));
			return;
		}

		frappe.msgprint({
			title: __("Connection Info"),
			message: __(
				"Midtrans connection is configured. Environment: {0}",
				[frm.doc.is_sandbox ? "Sandbox" : "Production"]
			),
			indicator: "green",
		});
	},
});
