import frappe
from frappe import _
def validate_mobile_no(doc, action):
    if doc.mobile_no:
        # if not (doc.mobile_no.is_digit() and len(doc.mobile_no) == 11):
        if len(doc.mobile_no) != 11:
            frappe.throw(_('Kindly enter a valid mobile number'))