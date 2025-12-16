"""
Bank Payment Advice DocType Controller

Implements accounting-safe calculations for payment amounts, TDS, and received amounts.
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from bank_payment_parser.utils.validation import validate_duplicate, make_read_only


class BankPaymentAdvice(Document):
	"""
	Bank Payment Advice document controller with accounting calculations.
	"""
	
	def validate(self):
		"""Validate document and calculate accounting fields."""
		validate_duplicate(self)
		self._calculate_accounting_fields()
	
	def _calculate_accounting_fields(self):
		"""Calculate total TDS and total received amount from invoice table.
		
		Business Rule:
		- total_tds_amount = sum of all invoice TDS amounts
		- total_received_amount = payment_amount - total_tds_amount
		
		This ensures accounting accuracy and audit readiness.
		"""
		# Sum TDS from invoice table
		total_tds = 0.0
		if self.invoices:
			for invoice in self.invoices:
				# Support both old field (tds_wct) and new field (invoice_tds_amount)
				tds = invoice.get("invoice_tds_amount") or invoice.get("tds_wct") or 0.0
				total_tds += float(tds) if tds else 0.0
		
		self.total_tds_amount = total_tds
		
		# Calculate total received amount
		# total_received_amount = payment_amount - total_tds_amount
		payment_amt = float(self.payment_amount or 0)
		self.total_received_amount = max(payment_amt - total_tds, 0.0)
	
	def on_submit(self):
		"""Handle document submission."""
		make_read_only(self)
	
	def before_save(self):
		"""Set default values before save."""
		if not self.parse_status:
			self.parse_status = "Draft"
	
	def on_trash(self):
		"""Prevent direct deletion of Bank Payment Advice records.
		
		Advice records should only be deleted when their parent
		Bank Payment Bulk Upload is cancelled. This prevents orphan
		records and maintains data integrity.
		
		Exception: Allow deletion if explicitly marked for bulk cleanup
		(via flags.bulk_cleanup) to support automatic cleanup from bulk upload.
		
		Also allows deletion if:
		- The record is in draft (docstatus = 0) and has no bulk_upload_reference
		- The record has no bulk_upload_reference (single upload)
		"""
		# Allow deletion if this is part of bulk cleanup process
		if getattr(frappe.flags, "bulk_cleanup", False):
			return
		
		# Allow deletion if no bulk upload reference (single file upload)
		if not self.bulk_upload_reference:
			return
		
		# If this advice was created from a bulk upload, prevent direct deletion
		# Check if parent bulk upload still exists
		parent_exists = frappe.db.exists("Bank Payment Bulk Upload", self.bulk_upload_reference)
		
		if parent_exists:
			frappe.throw(
				_(
					"Cannot delete Bank Payment Advice '{0}' directly. "
					"Please cancel the parent Bulk Upload '{1}' to delete this record."
				).format(self.name, self.bulk_upload_reference),
				title=_("Deletion Not Allowed")
			)
		else:
			# Parent doesn't exist, allow deletion but warn
			frappe.msgprint(
				_("Warning: Deleting advice record '{0}' whose parent bulk upload no longer exists.").format(self.name),
				indicator="orange",
				alert=True
			)
