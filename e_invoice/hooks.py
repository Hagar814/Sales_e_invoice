from . import __version__ as app_version

app_name = "e_invoice"
app_title = "E Invoice"
app_publisher = "alaabadry1@gmail.com "
app_description = "Frappe application to manage einvoicing"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "alaabadry1@gmail.com "
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/e_invoice/css/e_invoice.css"
# app_include_js = "/assets/e_invoice/js/e_invoice.js"

# include js, css files in header of web template
# web_include_css = "/assets/e_invoice/css/e_invoice.css"
# web_include_js = "/assets/e_invoice/js/e_invoice.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "e_invoice/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "e_invoice.install.before_install"
# after_install = "e_invoice.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "e_invoice.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		#"before_save": "e_invoice.custom.python.sales_invoice.validate_tax",
		# "before_save": "e_invoice.custom.python.sales_invoice.before_save",
		"validate": "e_invoice.custom.python.calc_invoice_value.calc_invoice_value",
		"on_submit":"e_invoice.custom.python.sales_invoice.on_submit"
	},
	"Sales Order": {
		#"onload": "e_invoice.custom.python.calc_outstanding.calc_outstanding"
	},
	"Customer": {
		"validate": "e_invoice.custom.python.customer_quick_entry.validate_mobile_no"
		}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"e_invoice.tasks.all"
# 	],
# 	"daily": [
# 		"e_invoice.tasks.daily"
# 	],
# 	"hourly": [
# 		"e_invoice.tasks.hourly"
# 	],
# 	"weekly": [
# 		"e_invoice.tasks.weekly"
# 	]
# 	"monthly": [
# 		"e_invoice.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "e_invoice.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "e_invoice.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "e_invoice.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

fixtures = [{
	"doctype": "Role",
	"filters": {
		"name": ["in", "E-invoice"]
	}
	},
	{
	"doctype": "Custom DocPerm",
	"filters": {
		"role": ["in", "E-invoice"]
	}
	},
	{
        'dt': 'Custom Field',
        'filters': {
            'name': ['in', [
				'Customer-e_invoice_info',
                'Customer-street',
				'Customer-region_city',
				'Customer-building_number',
				'Customer-country',
				'Customer-country_code',
				'Customer-customer_types',
				'Customer-e_invoice_info_1',
    			'Customer-tax_id',
                'Item-code',
				'Item-item_type',
				'Item Tax Template-type',
				'Item Tax Template-tax_rate',
				'Item Tax Template-sub_type',
				'Sales Invoice-customer_types',
				'Sales Invoice-e_invoice',
				'Sales Invoice-uuid',
				'Sales Invoice-check_migrate',
				'Sales Invoice-cduuid',
				'Sales Invoice-column_break_33',
				'Sales Invoice-submission_id',
				'Sales Invoice-is_valid',
				'Sales Invoice-tn_id',
				'Sales Invoice-e_invoice_process_status',
				'Sales Invoice Item-item_type',
				'Sales Invoice Item-code',
				'Sales Invoice Item-type',
				'Sales Invoice Item-sub_type',
				'Sales Invoice Item-tax_rate',
				'Sales Invoice Item-tax_amount',
				'Sales Invoice Item-total_amount',
				'Sales Invoice Item-discount_after',
				'Sales Invoice Item-discount_before',
				'Sales Invoice Item-tax_uom',

            ]]
        }
    }

	]
# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"e_invoice.auth.validate"
# ]
doctype_list_js = {
	"Sales Invoice" : "custom/js/sales_invoice_list.js",
}
doctype_js = {"Sales Invoice" : "custom/js/sales_invoice.js"}
#after_install = "e_invoice.custom.python.custom_fields.make_custom_fields"
