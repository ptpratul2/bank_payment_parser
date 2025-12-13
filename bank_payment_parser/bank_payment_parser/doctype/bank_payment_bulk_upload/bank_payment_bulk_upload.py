"""
Bank Payment Bulk Upload DocType Controller
"""

import frappe
from frappe import _
from frappe.utils import now, get_datetime
from bank_payment_parser.jobs.bulk_processor import enqueue_bulk_processing


class BankPaymentBulkUpload(frappe.model.document.Document):
	"""Controller for Bank Payment Bulk Upload"""
	
	def validate(self):
		"""Validate bulk upload record"""
		if not self.items:
			frappe.throw(_("Please add at least one PDF file to upload"))
		
		# Set total files count
		self.total_files = len(self.items)
		
		# Initialize counters if new
		if self.is_new():
			self.processed_files = 0
			self.success_count = 0
			self.failed_count = 0
			self.status = "Queued"
			self.uploaded_by = frappe.session.user
			self.upload_time = now()
			
			# Set file names from attachments
			for item in self.items:
				if item.pdf_file and not item.file_name:
					# Extract file name from file URL
					file_name = item.pdf_file.split("/")[-1]
					item.file_name = file_name
					item.parse_status = "Pending"
	
	def on_submit(self):
		"""Start background processing when document is submitted"""
		if self.status == "Queued":
			# Enqueue background jobs for all items
			enqueue_bulk_processing(self.name)
			frappe.msgprint(
				_("Bulk upload processing has been queued. Files will be processed in the background."),
				indicator="blue",
				alert=True
			)
	
	def update_status(self):
		"""Update status based on child items"""
		# Reload to get latest data
		self.reload()
		
		processed = 0
		success = 0
		failed = 0
		
		for item in self.items:
			if item.parse_status in ["Success", "Failed"]:
				processed += 1
				if item.parse_status == "Success":
					success += 1
				else:
					failed += 1
		
		self.processed_files = processed
		self.success_count = success
		self.failed_count = failed
		
		# Determine overall status
		if processed == 0:
			self.status = "Queued"
		elif processed < self.total_files:
			self.status = "Processing"
		elif success == self.total_files:
			self.status = "Completed"
		elif failed == self.total_files:
			self.status = "Failed"
		else:
			self.status = "Partial"
		
		self.save(ignore_permissions=True)
		frappe.db.commit()
	
	def reprocess_failed(self):
		"""Reprocess all failed items"""
		failed_items = [item for item in self.items if item.parse_status == "Failed"]
		
		if not failed_items:
			frappe.msgprint(_("No failed items to reprocess"))
			return
		
		# Reset failed items
		for item in failed_items:
			item.parse_status = "Pending"
			item.error_message = ""
			item.parsed_document = ""
			item.parser_used = ""
		
		self.save(ignore_permissions=True)
		frappe.db.commit()
		
		# Re-enqueue processing
		enqueue_bulk_processing(self.name, reprocess=True)
		
		frappe.msgprint(
			_("Reprocessing {0} failed file(s)").format(len(failed_items)),
			indicator="blue",
			alert=True
		)
