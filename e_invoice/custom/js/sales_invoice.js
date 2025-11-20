frappe.ui.form.on('Sales Invoice', {
    update_tax: function (frm) {
        const set_fields = [
          "account_head",
          "tax_amount",
        ];
        const custom_fields = [
        'item',
		'tax_template',
		'amount',
        'tax_wise_amount',
        'account_head'
          ];
        frappe.call({
          method: "e_invoice.custom.python.sales_invoice.update_tax",
          args: {
            doc: frm.doc,
          },
          freeze: true,
          callback: function (r) {
            console.log(r.message);
            if (r.message[0]) {
              frm.set_value("custom_tax_listing", []);
              $.each(r.message[0], function (i, d) {
                var row = frm.add_child("custom_tax_listing");
                for (let key in d) {
                  if (d[key] && in_list(set_fields, key)) {
                    row[key] = d[key];
                  }
                }
              });
            }
            if (r.message[1]) {
            frm.set_value("e_invoice_item_wise_tax_details", []);
              $.each(r.message[1], function (j, val) {
                var row1 = frm.add_child("e_invoice_item_wise_tax_details");
                for (let key1 in val) {
                  if (val[key1] && in_list(custom_fields, key1)) {
                    row1[key1] = val[key1];
                  }
                }
              });
            }
            refresh_field("custom_tax_listing");
            refresh_field("e_invoice_item_wise_tax_details");
          },
        });
      },
    refresh: function (frm) {
        if (frm.doc.docstatus == 0) {
            frm.add_custom_button(__('Send Invoice'), function () {
                frappe.confirm(
                    __('Are you sure you want to send this invoice?'),
                    function () {
                        frappe.call({
                            method:
                                "e_invoice.custom.python.sales_invoice.post_invoice",
                            freeze: true,
                            args: {
                                'docnames': [frm.doc.name]
                            },
                            callback: function (data) {
                                if (!data.exc) {
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __("E-Invoice")).addClass("btn-warning").css({ 'color': 'green', 'font-weight': 'bold' });
        }
        if (frm.doc.uuid) {
                frm.add_custom_button(__('Validate Invoice'), function () {
                    frappe.confirm(
                        __('Are you sure you want to validate this invoice?'),
                        function () {
                            frappe.call({
                                method:
                                    "e_invoice.custom.python.sales_invoice.validate_einvoice",
                                freeze: true,
                                args: {
                                    'docnames': [frm.doc.name]
                                },
                                callback: function (data) {
                                    if (!data.exc) {
                                        frm.reload_doc();
                                        frappe.msgprint(__("Record validated successfully"));
                                    }
                                }
                            });
                        }
                    );
                }, __("E-Invoice")).addClass("btn-warning").css({ 'color': 'green', 'font-weight': 'bold' });
            }
        
        if (frm.doc.docstatus == 1) {
            frm.add_custom_button(__('Debit Note'), function () {
                frappe.confirm(
                    __('Are you sure you want to send debit note?'),
                    function () {
                        frappe.call({
                            method:
                                "e_invoice.custom.python.sales_invoice.post_invoice",
                            freeze: true,
                            args: {
                                'docnames': [frm.doc.name]
                            },
                            callback: function (data) {
                                if (!data.exc) {
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __("E-Invoice")).addClass("btn-warning").css({ 'color': 'green', 'font-weight': 'bold' });
        }
            if (frm.doc.is_return){
                frm.add_custom_button(__('Credit Note'), function () {
                    frappe.confirm(
                        __('Are you sure you want to send credit note?'),
                        function () {
                            frappe.call({
                                method:
                                    "e_invoice.custom.python.sales_invoice.credit_note",
                                freeze: true,
                                args: {
                                    'docnames': [frm.doc.name]
                                },
                                callback: function (data) {
                                    if (!data.exc) {
                                        frm.reload_doc();
                                    }
                                }
                            });
                        }
                    );
                }, __("E-Invoice")).addClass("btn-warning").css({ 'color': 'green', 'font-weight': 'bold' });
            }

            frm.add_custom_button(__('Cancel Invoice'), function () {
                frappe.confirm(
                    __('Are you sure you want to cancel submitted invoice?'),
                    function () {
                        frappe.call({
                            method:
                                "e_invoice.custom.python.sales_invoice.cancel",
                            freeze: true,
                            args: {
                                'docnames': [frm.doc.name]
                            },
                            callback: function (data) {
                                if (!data.exc) {
                                    frm.reload_doc();
                                }
                            }
                        });
                    }
                );
            }, __("E-Invoice")).addClass("btn-warning").css({ 'color': 'red', 'font-weight': 'bold' });

            cur_frm.page.set_inner_btn_group_as_primary(__('E-Invoice'));
        },
   before_save: function(frm) {
    

       // 1️⃣ Fetch customer fields
       frappe.call({
           method: "frappe.client.get",
           args: { doctype: "Customer", name: frm.doc.customer },
           callback: function(r) {
               if (!r.message) return;

               const customer_doc = r.message;

               // Set customer_type and tn_id if empty
               if (!frm.doc.customer_types && customer_doc.customer_types) {
                   frm.set_value("customer_types", customer_doc.customer_types);
               }
               if (!frm.doc.tn_id && customer_doc.tax_id) {
                   frm.set_value("tn_id", customer_doc.tax_id);
               }

               frm.refresh_field("customer_types");
               frm.refresh_field("tn_id");
           }
       });

       // 2️⃣ Loop through all items in the child table
       frm.doc.items.forEach((row) => {
           if (!row.item_code) return;

           frappe.call({
               method: "frappe.client.get",
               args: { doctype: "Item", name: row.item_code },
               callback: function(r) {
                   if (!r.message) return;

                   const item_doc = r.message;

                   // Set item_type and code if empty
                   if (!row.item_type && item_doc.item_type) {
                       frappe.model.set_value(row.doctype, row.name, "item_type", item_doc.item_type);
                   }
                   if (!row.code && item_doc.item_code) {
                       frappe.model.set_value(row.doctype, row.name, "code", item_doc.item_code);
                   }

               }
           });
       });
   }
});
frappe.ui.form.on('Sales Invoice', 'validate', function(frm) {
var regex = /^\d{9}$/;
if (regex.test(frm.doc.tn_id) === false && (frm.doc.customer_type == 'B')) 
{
    
    frappe.msgprint(__("Tax Id Must be 9 digit."+ "<br>"+".رقم التسجيل يجب ان لا يقل عن 9 ارقام"));
    frappe.validated = true;
}
var regex = /^\d{14}$/;
if (regex.test(frm.doc.tax_id) === false && (frm.doc.customer_type == 'P') && (frm.doc.customer_type > 50000)) 
{
    frappe.msgprint(__("Customer Id Must be 14 digit."+ "<br>"+".الرقم القومي يجب ان يكون مكون من 14 رقم"));
    frappe.validated = false;
}
});

// cur_frm.add_fetch('item_code',  'item_type',  'item_type');
// cur_frm.add_fetch('item_code',  'code',  'code');

frappe.ui.form.on("Sales Invoice Item", {
    item_code: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];

        let filters = {
            'item_code': d.item_code,
            'valid_from': ["<=", frm.doc.transaction_date || frm.doc.bill_date || frm.doc.posting_date],
            'item_group': d.item_group,
        }

        if (frm.doc.tax_category)
            filters['tax_category'] = frm.doc.tax_category;
        if (frm.doc.company)
            filters['company'] = frm.doc.company;



        frappe.call({
            method: 'e_invoice.custom.python.sales_invoice.get_default_tax_template_values',
            freeze: true,
            args: {
                filters: filters
            },
            callback: function(r) {
                if (r.message) {
                    frappe.model.set_value(cdt, cdn, 'item_tax_template', r.message[0]);
                    frappe.model.set_value(cdt, cdn, 'type', r.message[1]);
                    frappe.model.set_value(cdt, cdn, 'subtype', r.message[2]);
                    frappe.model.set_value(cdt, cdn, 'tax_rate', r.message[3]);
                    frm.refresh_field('items');
                }
            }
        });
        d.amount = flt(d.rate) *  flt(d.qty);
        d.net_rate = flt(d.rate) ;
        d.net_amount = flt(d.net_rate) *  flt(d.qty) - flt(d.discount_before);
        d.tax_amount = flt(d.net_amount) * flt(d.item_tax_rate) /100;
        d.total_amount = flt(d.tax_amount) + flt(d.net_amount) - flt(d.discount_after);
        frappe.model.set_value(cdt, cdn, 'net_rate', (flt(d.rate)));
        frappe.model.set_value(cdt, cdn, 'net_amount', (flt(d.net_rate) *  flt(d.qty)  - flt(d.discount_before)));
        frappe.model.set_value(cdt, cdn, 'tax_amount', (flt(d.net_amount) * flt(d.item_tax_rate)/100));
        frappe.model.set_value(cdt, cdn, 'total_amount', (flt(d.tax_amount) + flt(d.net_amount) - flt(d.discount_after)));
        frm.refresh_field("items");
        frm.refresh_field("item_tax_template"); 
    },
    item_tax_template: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        d.amount = flt(d.rate) *  flt(d.qty);
        d.net_rate = flt(d.rate);
        d.net_amount = flt(d.net_rate) *  flt(d.qty) - flt(d.discount_before);
        d.tax_amount = flt(d.net_amount) * flt(d.tax_rate) /100;
        d.total_amount = flt(d.tax_amount) + flt(d.net_amount) - flt(d.discount_after);
        frappe.model.set_value(d.doctype, d.name, 'net_rate', (flt(d.rate) ));
        frappe.model.set_value(d.doctype, d.name, 'net_amount', (flt(d.net_rate) *  flt(d.qty) - flt(d.discount_before)));
        frappe.model.set_value(d.doctype, d.name, 'tax_amount', (flt(d.net_amount) * flt(d.tax_rate)/100));
        frappe.model.set_value(d.doctype, d.name, 'total_amount', (flt(d.tax_amount) + flt(d.net_amount) - flt(d.discount_after)));
        frm.refresh_field("items"); 
    },
    discount_before: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
       
        d.amount = flt(d.rate) *  flt(d.qty);
        d.net_rate = flt(d.rate);
        d.net_amount = flt(d.net_rate) *  flt(d.qty) - flt(d.discount_before);
        d.tax_amount = flt(d.net_amount) * flt(d.tax_rate) /100;
        d.total_amount = flt(d.tax_amount) + flt(d.net_amount) - flt(d.discount_after);
        frappe.model.set_value(d.doctype, d.name, 'net_rate', (flt(d.rate)));
        frappe.model.set_value(d.doctype, d.name, 'net_amount', (flt(d.net_rate) *  flt(d.qty) - flt(d.discount_before)));
        frappe.model.set_value(d.doctype, d.name, 'tax_amount', (flt(d.net_amount) * flt(d.tax_rate)/100));
        frappe.model.set_value(d.doctype, d.name, 'total_amount', (flt(d.tax_amount) + flt(d.net_amount) - flt(d.discount_after)));
        
        
        frm.refresh_field("items"); 

    },
    
    discount_after: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
       
        d.amount = flt(d.rate) *  flt(d.qty);
        d.net_rate = flt(d.rate);
        d.net_amount = flt(d.net_rate) *  flt(d.qty) - flt(d.discount_before);
        d.tax_amount = flt(d.net_amount) * flt(d.tax_rate) /100;
        d.total_amount = flt(d.tax_amount) + flt(d.net_amount) - flt(d.discount_after);
        frappe.model.set_value(d.doctype, d.name, 'net_rate', (flt(d.rate)));
        frappe.model.set_value(d.doctype, d.name, 'net_amount', (flt(d.net_rate) *  flt(d.qty)- flt(d.discount_before)));
        frappe.model.set_value(d.doctype, d.name, 'tax_amount', (flt(d.net_amount) * flt(d.tax_rate)/100));
        frappe.model.set_value(d.doctype, d.name, 'total_amount', (flt(d.tax_amount) + flt(d.net_amount) - flt(d.discount_after))); 
        frm.refresh_field("items");
    
    }

});
