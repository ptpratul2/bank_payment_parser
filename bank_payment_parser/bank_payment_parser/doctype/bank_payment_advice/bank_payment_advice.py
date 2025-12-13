"""
Bank Payment Advice DocType Controller
"""

import frappe
from frappe.model.document import Document
from bank_payment_parser.utils.validation import validate_duplicate, make_read_only


class BankPaymentAdvice(Document):
	"""
	Bank Payment Advice document controller.
	"""
	
	def validate(self):
		"""Validate document before save."""
		validate_duplicate(self)
	
	def on_submit(self):
		"""Handle document submission."""
		make_read_only(self)
	
	def before_save(self):
		"""Set default values before save."""
		if not self.parse_status:
			self.parse_status = "Draft"
