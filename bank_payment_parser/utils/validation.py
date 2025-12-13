"""
Validation utilities for Bank Payment Advice doctype.
"""

import frappe
from frappe.model.document import Document


def validate_duplicate(doc, method=None):
	"""
	Validate that UTR/RRN or Bank Ref No is unique.
	
	Prevents duplicate payment advice records.
	"""
	if doc.is_new():
		# Check for duplicate UTR/RRN
		if doc.utr_rrn_no:
			existing = frappe.db.exists(
				"Bank Payment Advice",
				{"utr_rrn_no": doc.utr_rrn_no, "name": ["!=", doc.name]}
			)
			if existing:
				frappe.throw(
					f"Payment Advice with UTR/RRN '{doc.utr_rrn_no}' already exists: {existing}",
					title="Duplicate UTR/RRN"
				)
		
		# Check for duplicate Bank Reference No
		if doc.bank_reference_no:
			existing = frappe.db.exists(
				"Bank Payment Advice",
				{"bank_reference_no": doc.bank_reference_no, "name": ["!=", doc.name]}
			)
			if existing:
				frappe.throw(
					f"Payment Advice with Bank Reference No '{doc.bank_reference_no}' already exists: {existing}",
					title="Duplicate Bank Reference"
				)


def make_read_only(doc, method=None):
	"""
	Make document read-only after submission.
	"""
	# This is handled by Frappe's standard permissions
	# But we can add additional logic here if needed
	pass
