app_name = "project_costing"
app_title = "Project Costing"
app_publisher = "Finbyz"
app_description = "Cost Control Management"
app_email = "info@finbyz.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "project_costing",
# 		"logo": "/assets/project_costing/logo.png",
# 		"title": "Project Costing",
# 		"route": "/project_costing",
# 		"has_permission": "project_costing.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/project_costing/css/project_costing.css"
app_include_js = [
    "https://cdn.jsdelivr.net/npm/chart.js",
]
# include js, css files in header of web template
# web_include_css = "/assets/project_costing/css/project_costing.css"
# web_include_js = "/assets/project_costing/js/project_costing.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "project_costing/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Project" : "public/js/project.js",
              "Material Request":"public/js/material_request.js",
              "Request for Quotation":"public/js/request_for_quotation",
              "Supplier Quotation":"public/js/supplier_quotation.js",
              "Purchase Receipt":"public/js/purchase_receipt.js",
              "Purchase Invoice":"public/js/purchase_invoice.js",
              "Stock Entry":"public/js/stock_entry.js",
              "Expense Claim":"public/js/expense_claim.js",
              "Purchase Order":"public/js/purchase_order.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
doctype_tree_js = {"WBS item" : "public/js/wbs_item_tree.js",
                   "BOQ Details": "public/js/boq_detail.js",}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "project_costing/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "project_costing.utils.jinja_methods",
# 	"filters": "project_costing.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "project_costing.install.before_install"
# after_install = "project_costing.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "project_costing.uninstall.before_uninstall"
# after_uninstall = "project_costing.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "project_costing.utils.before_app_install"
# after_app_install = "project_costing.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "project_costing.utils.before_app_uninstall"
# after_app_uninstall = "project_costing.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "project_costing.notifications.get_notification_config"

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
    "WBS item": {
        "validate": "project_costing.project_costing.doc_events.wbs_item.validate"
    },
    "Material Request": {
        "on_update": "project_costing.project_costing.doc_events.material_request.on_update"
    },    
    "Purchase Order": {
        "on_update": "project_costing.project_costing.doc_events.purchase_order.on_update"
    },
    "Purchase Receipt": {
        "on_update": "project_costing.project_costing.doc_events.purchase_receipt.on_update"
    },
    "Stock Entry": {
        "on_update": "project_costing.project_costing.doc_events.stock_entry.on_update"
    },
}
# doc_events = {
# 	"Material Request":{
#         "on_submit": "project_costing.project_costing.doc_events.material_request.on_submit",
#         "on_cancel": "project_costing.project_costing.doc_events.material_request.on_cancel"
#     },
#     "Purchase Order":{ 
#         "on_submit": "project_costing.project_costing.doc_events.purchase_order.on_submit",
#         "on_cancel": "project_costing.project_costing.doc_events.purchase_order.on_cancel"
#     },
#      "Purchase Receipt":{ 
#         "on_submit": "project_costing.project_costing.doc_events.purchase_receipt.on_submit",
#         "on_cancel": "project_costing.project_costing.doc_events.purchase_receipt.on_cancel"
#     },
#      "Stock Entry":{ 
#         "on_submit": "project_costing.project_costing.doc_events.stock_entry.on_submit",
#         "on_cancel": "project_costing.project_costing.doc_events.stock_entry.on_cancel"
#     }
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"project_costing.project_costing.doctype.wbs_item.wbs_item.update_wbs_items",
	]
}
# scheduler_events = {
# 	"all": [
# 		"project_costing.tasks.all"
# 	],
# 	"daily": [
# 		"project_costing.tasks.daily"
# 	],
# 	"hourly": [
# 		"project_costing.tasks.hourly"
# 	],
# 	"weekly": [
# 		"project_costing.tasks.weekly"
# 	],
# 	"monthly": [
# 		"project_costing.tasks.monthly"
# 	],
# }
treeviews = ["WBS item"]
# Testing
# -------

# before_tests = "project_costing.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "project_costing.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "project_costing.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["project_costing.utils.before_request"]
# after_request = ["project_costing.utils.after_request"]

# Job Events
# ----------
# before_job = ["project_costing.utils.before_job"]
# after_job = ["project_costing.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"project_costing.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

