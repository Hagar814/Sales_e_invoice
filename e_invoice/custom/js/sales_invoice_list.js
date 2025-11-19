frappe.listview_settings['Sales Invoice'] = {
    onload: function (list_view) {
        list_view.page
            .add_inner_button(__("View E-Invoice Logs"), function () {
                window.open("/app/e-invoice-log")
            }).addClass("btn btn-primary btn-sm primary-action");
        const action = () => {
            const selected_docs = list_view.get_checked_items();
            const docnames = list_view.get_checked_items(true);

            for (let doc of selected_docs) {
                if (doc.docstatus === 2) {
                    frappe.throw(__("Bulk document submission not allowed for a cancelled document"));
                }
            }

            frappe.confirm(
                __('Are you sure you want to send all selected invoices?'),
                function () {
                    frappe.call({
                        method:
                            "e_invoice.custom.python.e_invoice_enqueue.post_invoice",
                        freeze: true,
                        freeze_message: __("Processing ..."),
                        args: {
                            'docnames': docnames
                        },
                        callback: function (r) {
                            if (r.message) {
                                frappe.msgprint(__(`Documents Queued successfully! <a href="/app/e-invoice-log/${r.message}">View Logs</a>`))
                            }
                        }
                    });
                }
            );
        };

        list_view.page.add_actions_menu_item(__('E-Invoice Bulk Send'), action, false);

        const cancel_action = () => {
            const selected_docs = list_view.get_checked_items();
            const docnames = list_view.get_checked_items(true);

            frappe.confirm(
                __('Are you sure you want to cancel all selected invoices?'),
                function () {
                    frappe.call({
                        method:
                            "e_invoice.custom.python.e_invoice_enqueue.cancel",
                        freeze: true,
                        freeze_message: __("Processing ..."),
                        args: {
                            'docnames': docnames
                        },
                        callback: function (r) {
                            if (r.message) {
                                frappe.msgprint(__(`Documents Queued successfully! <a href="/app/e-invoice-log/${r.message}">View Logs</a>`))
                            }
                        }
                    });
                }
            );
        };

        list_view.page.add_actions_menu_item(__('E-Invoice Bulk Cancel'), cancel_action, false);

        const credit_action = () => {
            const selected_docs = list_view.get_checked_items();
            const docnames = list_view.get_checked_items(true);

            frappe.confirm(
                __('Are you sure you want to make credit note for all selected invoices?'),
                function () {
                    frappe.call({
                        method:
                            "e_invoice.custom.python.e_invoice_enqueue.credit_note",
                        freeze: true,
                        freeze_message: __("Processing ..."),
                        args: {
                            'docnames': docnames
                        },
                        callback: function (r) {
                            if (r.message) {
                                frappe.msgprint(__(`Documents Queued successfully! <a href="/app/e-invoice-log/${r.message}">View Logs</a>`))
                            }
                        }
                    });
                }
            );
        };

        list_view.page.add_actions_menu_item(__('E-Invoice Bulk Credit'), credit_action, false);

        const validate_action = () => {
            const selected_docs = list_view.get_checked_items();
            const docnames = list_view.get_checked_items(true);

            frappe.confirm(
                __('Are you sure you want to make Validate for all selected invoices?'),
                function () {
                    frappe.call({
                        method:
                            "e_invoice.custom.python.e_invoice_enqueue.validate",
                        freeze: true,
                        freeze_message: __("Processing ..."),
                        args: {
                            'docnames': docnames
                        },
                        callback: function (r) {
                            if (r.message) {
                                frappe.msgprint(__(`Documents Queued successfully! <a href="/app/e-invoice-log/${r.message}">View Logs</a>`))
                            }
                        }
                    });
                }
            );
        };

        list_view.page.add_actions_menu_item(__('E-Invoice Bulk Validate'), validate_action, false);
    }
}
