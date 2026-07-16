app_name = "ampower_form_builder"
app_title = "Ampower Form Builder"
app_publisher = "Ambibuzz Technologies LLP"
app_description = "Drag-and-drop dynamic form builder for Frappe/ERPNext. Stores form schemas and submissions as JSON — no DocType pollution."
app_email = "buzz@ambibuzz.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# Assets for the Form Builder page are loaded explicitly from the page controller.
app_include_js = "ampower_form_builder.bundle.js"
app_include_css = "ampower_form_builder.bundle.css"

# include js, css files in header of web template
# web_include_css = "/assets/ampower_form_builder/css/ampower_form_builder.css"
# web_include_js = "/assets/ampower_form_builder/js/ampower_form_builder.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ampower_form_builder/public/scss/website"

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

# Fixtures
# --------
fixtures = [
    {"dt": "Role", "filters": [["name", "in", ["Form Builder Admin", "Form Builder User"]]]},
]

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
# 	"methods": "ampower_form_builder.utils.jinja_methods",
# 	"filters": "ampower_form_builder.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ampower_form_builder.install.before_install"
# after_install = "ampower_form_builder.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "ampower_form_builder.uninstall.before_uninstall"
# after_uninstall = "ampower_form_builder.uninstall.after_uninstall"

# Document Events
# ---------------

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {}

# Testing
# -------

# before_tests = "ampower_form_builder.install.before_tests"

# Overriding Methods
# ------------------------------

# override_whitelisted_methods = {}

# exempt linked doctypes from being automatically cancelled
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# ignore_links_on_delete = ["Communication", "ToDo"]

# User Data Protection
# --------------------

# user_data_fields = []

# Authentication and authorization
# --------------------------------

# auth_hooks = []
