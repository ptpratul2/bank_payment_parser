app_name = "bank_payment_parser"
app_title = "Bank Payment Parser"
app_publisher = "Frappe"
app_description = "Scalable bank payment advice PDF parser with customer-specific parsing"
app_email = "support@frappe.io"
app_license = "mit"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/bank_payment_parser/css/bank_payment_parser.css"
app_include_js = "/assets/bank_payment_parser/js/bank_payment_parser.js"

# include js in doctype views
doctype_js = {
	"Bank Payment Advice": "public/js/bank_payment_advice.js"
}

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"Bank Payment Advice": "bank_payment_parser.overrides.bank_payment_advice.CustomBankPaymentAdvice"
# }

# Document Events
# ---------------
doc_events = {
	"Bank Payment Advice": {
		"on_submit": "bank_payment_parser.utils.validation.make_read_only",
		"validate": "bank_payment_parser.utils.validation.validate_duplicate"
	}
}

# Scheduled Tasks
# ---------------
# scheduler_events = {
# 	"daily": [
# 		"bank_payment_parser.tasks.daily"
# 	]
# }

# Testing
# -------
# before_tests = "bank_payment_parser.install.before_tests"
