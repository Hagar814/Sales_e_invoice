// Copyright (c) 2022, alaabadry1@gmail.com  and contributors
// For license information, please see license.txt

frappe.ui.form.on('E Invoice Log', {
	refresh: function (frm) {
		frm.disable_form()
		frm.fields_dict.invoices.grid.toggle_checkboxes(1)
		frm.add_custom_button("Resend Failed Invoices", ResendFailed, "Action");
		frm.add_custom_button("Resend Selected Invoices", ResendSelected, "Action");
		if (frm.doc.doc_under_process) {
			frm.add_custom_button("Cancel the Process",
				async function () {
					frappe.confirm(
						`Do you want to cancel this Process?`,
						async function () {
							await frappe.call({
								method: "e_invoice.e_invoice.doctype.e_invoice_log.e_invoice_log.cancel_queue",
								args: {
									docname: frm.doc.name,
								},
								callback: function (r) {
									frm.reload_doc();
								}
							});
						});
				});
			frm.add_custom_button("Cancel the Selected Invoices",
				async function () {
					let invoices = [];
					cur_frm.fields_dict.invoices.grid.get_selected_children().forEach(row => {
						invoices.push(row.invoice_no);
					});
					if (invoices.length == 0) {
						frappe.show_alert({ message: "Please Select the Invoices", indicator: "red" });
						return;
					}
					frappe.confirm(
						`Do you want to cancel the selected invoices and execute other invoice in another queue?`,
						async function () {
							await frappe.call({
								method: "e_invoice.e_invoice.doctype.e_invoice_log.e_invoice_log.cancel_selected",
								args: {
									docname: frm.doc.name,
									docnames: invoices,
								},
								callback: function (r) {
									frm.reload_doc()
									if (r.message) {
										frappe.msgprint(__(`Documents queued successfully, <a href="/app/e-invoice-log/${r.message}">View Logs</a>`))
									}
									else {
										frappe.msgprint(__(`Something Went Wrong`))
									}
								}
							});
						});
				})
		}
		// setInterval(function() {
		// 	 frm.reload_doc(); 
		// 	}, 10000);
	}
});

function ResendFailed() {
	let invoices = [];
	(cur_frm.doc.invoices || []).forEach(row => {
		if (row.status != "Success") {
			invoices.push(row.invoice_no);
		}
	});
	ResendInvoices(invoices, cur_frm.doc.process1);
}


function ResendSelected() {
	let invoices = [];
	cur_frm.fields_dict.invoices.grid.get_selected_children().forEach(row => {
		invoices.push(row.invoice_no);
	})
	ResendInvoices(invoices, cur_frm.doc.process1);
}


async function ResendInvoices(invoices, process) {
	if (invoices.length == 0) {
		frappe.show_alert({ message: "Please Select the Invoices", indicator: "red" });
		return;
	}
	let method = "";
	if (process == "Einvoice Bulk Send") {
		method = "e_invoice.custom.python.e_invoice_enqueue.post_invoice";
	}
	else if (process == "Einvoice Bulk Cancel") {
		method = "e_invoice.custom.python.e_invoice_enqueue.cancel";
	}
	else if (process == "Einvoice Bulk Credit") {
		method = "e_invoice.custom.python.e_invoice_enqueue.credit_note";
	}
	else if (process == "Einvoice Bulk Validate") {
		method = "e_invoice.custom.python.e_invoice_enqueue.validate";
	}
	if (!method) {
		frappe.show_alert({ message: "Process not found!", indicator: "red" });
		return;
	}
	frappe.confirm(
		`Do you want to process this action: ${process}`,
		async function () {
			for (let row = 0; row < invoices.length; row++) {
				let cdt = cur_frm.doc.invoices[row].doctype,
					cdn = cur_frm.doc.invoices[row].name;
				frappe.model.set_value(cdt, cdn, 'status', 'Not Started')
			}
			await refresh_field('invoices')
			if (cur_frm.is_dirty()) {
				await cur_frm.save()
			}
			frappe.call({
				method: method,
				freeze: true,
				freeze_message: __("Processing ..."),
				args: {
					docnames: invoices,
					log: cur_frm.doc.name,
				},
				callback: function (r) {
					frappe.msgprint(__(`Documents Queued successfully!`))
					cur_frm.reload_doc();
					cur_frm.trigger("refresh");
				}
			});
		},)

}