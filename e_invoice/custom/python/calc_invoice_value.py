from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
import json
import frappe
import erpnext
from frappe import _, scrub
from frappe.utils import cint, flt, round_based_on_smallest_currency_fraction
from erpnext.controllers.accounts_controller import validate_conversion_rate, \
    validate_taxes_and_charges, validate_inclusive_tax
from erpnext.stock.get_item_details import _get_item_tax_template
from erpnext.accounts.doctype.pricing_rule.utils import get_applied_pricing_rules
from erpnext.accounts.doctype.journal_entry.journal_entry import get_exchange_rate


def calc_invoice_value(doc, method):
    doc.total_discount = doc.total_item_discount = doc.total_amount = doc.net_total = 0.0
    for d in doc.items:

        d.net_amount = flt(d.net_rate * d.qty -
                           d.discount_before, d.precision("net_amount"))
        tax = flt(d.base_net_amount) * flt(d.tax_rate)/100
        d.tax_amount = flt(tax, d.precision("tax_amount"))
        # if d.discount_amount:
        #     d.total_amount = flt(
        #         d.tax_amount + (d.price_list_rate * d.qty) - d.discount_after, d.precision("total_amount"))
        #     doc.total_amount = flt(doc.total) - flt(doc.discount_amount)
        if doc.discount_amount:
            d.total_amount = flt(
                d.tax_amount + d.base_amount - d.discount_after, d.precision("total_amount"))
            doc.total_amount = flt(doc.total) - flt(doc.discount_amount)
        else:
            d.total_amount = flt(
                d.tax_amount + d.base_net_amount - d.discount_after, d.precision("total_amount"))
            doc.total_amount += round(d.total_amount,2)
        #frappe.errprint(doc.total_amount)
        doc.total_discount += d.discount_before
        doc.total_item_discount += d.discount_after
        doc.net_total += d.net_amount

        frappe.db.commit()
        # frappe.throw(_('Thanks'))
        # frappe.errprint(['total',(doc.total_amount, d.total_amount, doc.discount_amount, doc.base_discount_amount)])
        # frappe.errprint(d.net_amount)
