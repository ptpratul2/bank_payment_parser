// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Bank Payment Advice", {
	refresh(frm) {
		// Show "Create Payment Entry" button if conditions are met
		if (
			frm.doc.docstatus === 1 &&
			frm.doc.parse_status === "Parsed" &&
			!frm.doc.payment_entry
		) {
			frm.add_custom_button(__("Create Payment Entry"), () => {
				frm.call({
					method: "bank_payment_parser.api.payment_entry.create_payment_entry",
					args: {
						advice_name: frm.doc.name,
					},
					callback: (r) => {
						if (r.message && r.message.success) {
							frappe.show_alert({
								message: __(r.message.message || "Payment Entry created successfully"),
								indicator: "green",
							});
							// Reload form to show payment_entry link
							frm.reload_doc();
							// Redirect to Payment Entry
							if (r.message.payment_entry) {
								setTimeout(() => {
									frappe.set_route("Form", "Payment Entry", r.message.payment_entry);
								}, 1000);
							}
						}
					},
					error: (r) => {
						frappe.show_alert({
							message: __(r.message || "Error creating Payment Entry"),
							indicator: "red",
						});
					},
				});
			}, __("Actions"));
		}

		// Show link to Payment Entry if it exists
		if (frm.doc.payment_entry) {
			frm.add_custom_button(__("View Payment Entry"), () => {
				frappe.set_route("Form", "Payment Entry", frm.doc.payment_entry);
			}, __("Actions"));
		}
	},
});
