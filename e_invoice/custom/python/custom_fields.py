from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
import frappe
from e_invoice.custom.python.sales_invoice import make_si_custom_fields

def make_custom_fields(update=True):
	make_si_custom_fields()
	custom_fields = {
		'Customer': [
		{
			'fieldname': 'street',
			'label': 'Street',
			'fieldtype': 'Data',
			'insert_after': 'customer_name',
            'reqd': 1,
            'translatable':1
		},
        {
			'fieldname': 'building_number',
			'label': 'Building Number',
			'fieldtype': 'Data',
			'insert_after': 'tax_id',
            'reqd': 1,
            'translatable':1
		},
        {
			'fieldname': 'region_city',
			'label': 'Region City',
			'fieldtype': 'Data',
			'insert_after': 'building_number',
            'reqd': 1,
            'translatable':1
		}
	],
    'Item': [
		{
			'fieldname': 'code',
			'label': 'Code',
			'fieldtype': 'Data',
			'insert_after': 'item_code',
            'reqd': 1,
            'translatable':1
		},
        {
			'fieldname': 'item_type',
			'label': 'Item Type',
			'fieldtype': 'Select',
            "options": "GS1\nEGS",
			'insert_after': 'naming_series',
            'reqd': 1,
            'translatable':1
		}
	],
    'Item Tax Template': [
		{
			'fieldname': 'rate',
			'label': 'Rate',
			'fieldtype': 'Select',
            "options": "0\n14\n10\n5\n8",
			'insert_after': 'title',
            'reqd': 1,
            'translatable':1
		},
        {
			'fieldname': 'column_break_1',
			'fieldtype': 'Column Break',
			'insert_after': 'taxes'
		},
        {
			'fieldname': 'type',
			'label': 'Type',
			'fieldtype': 'Select',
            "options": "T1\nT2\nT3\nT4\nT5\nT6\nT7\nT8\nT9\nT10\nT11\nT12",
			'insert_after': 'column_break_1',
            'reqd': 1,
            'translatable':1
		},
        {
			'fieldname': 'subtype',
			'label': 'Subtype',
			'fieldtype': 'Select',
            "options": "V001\nV002\nV003\nV004\nV005\nV006\nV007\nV008\nV009\nV010\nTbl01\nTbl02\nW001\nW002\nW003\nW004\nW005\nW006\nW007\nW008\nW009\nW010\nW011\nW012\nW013\nW014\nW015\nW016\nST01\nST02\nEnt01\nEnt02\nRD01\nRD02\nSC01\nSC02\nMn01\nMn02\nMI01\nMI02\nOF01\nOF02\nST03\nST04\nEnt03\nEnt04\nRD03\nRD04\nSC03\nSC04\nMn03\nMn04\nMI03\nMI04\nOF03\nOF04",
			'insert_after': 'type',
            'reqd': 1,
            'translatable':1
		}
	],
    'Sales Invoice Item': [
		{
			'fieldname': 'code',
			'label': 'Code',
			'fieldtype': 'Data',
			'insert_after': 'item_name',
            'fetch_from': 'item.code',
            'reqd': 1,
            'translatable': 1
		},
        {
			'fieldname': 'item_type',
			'label': 'Item Type',
			'fieldtype': 'Data',
			'insert_after': 'code',
            'fetch_from': 'item.item_type',
            'translatable': 1
		},
        {
			'fieldname': 'discount_before',
			'label': 'Discount Before',
			'fieldtype': 'Currency',
			'insert_after': 'amount'
		},
        {
			'fieldname': 'total_amount',
			'label': 'Total Amount',
			'fieldtype': 'Currency',
			'insert_after': 'discount_before',
            'read_only': 1
		},
        {
			'fieldname': 'type',
			'label': 'Type',
			'fieldtype': 'Data',
            'fetch_from': 'item_tax_template.type',
			'insert_after': 'item_tax_template',
            'translatable': 1
		},
        {
			'fieldname': 'tax_rate',
			'label': 'Tax Rate',
			'fieldtype': 'Int',
			'insert_after': 'type',
            'fetch_from': 'item_tax_template.rate',
            'read_only': 1
		},
        {
			'fieldname': 'discount_after',
			'label': 'Discount After',
			'fieldtype': 'Currency',
			'insert_after': 'stock_uom_rate'
		},
        {
			'fieldname': 'subtype',
			'label': 'Subtype',
			'fieldtype': 'Data',
			'insert_after': 'discount_after',
            'fetch_from': 'item_tax_template.subtype',
            'translatable': 1,
            'read_only': 1
		},
        {
			'fieldname': 'tax_amount',
			'label': 'Tax Amount',
			'fieldtype': 'Currency',
			'insert_after': 'subtype',
            'read_only': 1
		}
	],
    'Sales Invoice': [
		{
			'fieldname': 'is_valid',
			'label': 'Is Valid',
			'fieldtype': 'Check',
			'insert_after': 'cduuid',
			'read_only': 1
		},
		{
			'fieldname': 'customer_type',
			'label': 'Customer Type',
			'fieldtype': 'Select',
            "options": "B\nP",
			'insert_after': 'patient_name',
            'translatable': 1,
            'description': 'B Refer to B2B business\nP Refer to End Consumer Indivadual'
		},
    {
			'fieldname': 'building_number',
			'label': 'Building Number',
			'fieldtype': 'Data',
            'fetch_from': 'customer.building_number',
			'insert_after': 'tax_id',
            'reqd': 1,
            'translatable': 1
		},
        {
			'fieldname': 'street',
			'label': 'Street',
			'fieldtype': 'Data',
            'fetch_from': 'customer.street',
			'insert_after': 'building_number',
            'reqd': 1,
            'translatable': 1
		},
        {
			'fieldname': 'city',
			'label': 'City',
			'fieldtype': 'Data',
            'fetch_from': 'customer.city',
			'insert_after': 'street',
            'translatable': 1,
            'mandatory_depends_on': 'eval:doc.total>50000 && doc.customer_type == "P" || doc.customer_type == "B"'
		},
        {
			'fieldname': 'region_city',
			'label': 'Region City',
			'fieldtype': 'Data',
			'insert_after': 'city',
            'fetch_from': 'customer.region_city',
            'reqd': 1,
            'translatable': 1
		},
        {
			'fieldname': 'tn_id',
			'label': 'Tax ID/National ID',
			'fieldtype': 'Data',
            'fetch_from': 'customer.tax_id',
			'insert_after': 'company',
            'translatable': 1
		},
        {
			'fieldname': 'uuid',
			'label': 'UUID',
			'fieldtype': 'Data',
			'insert_after': 'due_date',
            'allow_on_submit': 1,
            'in_list_view': 1,
            'translatable': 1
		},
		{
			'fieldname': 'cduuid',
			'label': 'UUID',
			'fieldtype': 'Data',
			'insert_after': 'uuid',
            'allow_on_submit': 1,
            'in_list_view': 1,
            'translatable': 1
		},
        {
			'fieldname': 'total_discount',
			'label': 'Total Discount',
			'fieldtype': 'Currency',
			'insert_after': 'base_total_taxes_and_charges',
            'read_only': 1
		},
        {
			'fieldname': 'total_item_discount',
			'label': 'Total Item Discount',
			'fieldtype': 'Currency',
			'insert_after': 'total_discount',
            'read_only': 1
		},
        {
			'fieldname': 'total_amount',
			'label': 'Total Amount',
			'fieldtype': 'Currency',
			'insert_after': 'totals',
            'read_only': 1
		}
	]
	}
	create_custom_fields(
	custom_fields, ignore_validate=frappe.flags.in_patch, update=update)
