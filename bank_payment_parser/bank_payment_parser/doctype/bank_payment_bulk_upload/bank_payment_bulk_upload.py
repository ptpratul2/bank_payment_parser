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
		# Allow saving an empty draft so that files can be added via the
		# bulk upload dialog. Enforce at submit time only.
		if not self.items:
			if self.docstatus == 0:
				# Draft with no items is allowed
				self.total_files = 0
				self.processed_files = 0
				self.success_count = 0
				self.failed_count = 0
				return
			# On submit, at least one file (PDF or XML) is required
			frappe.throw(_("Please add at least one file to upload"))
		
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
	
	def on_cancel(self):
		"""Automatically cancel and delete all related Bank Payment Advice records.
		
		When a bulk upload is cancelled, all advice records created from it
		must be cleaned up to prevent orphan records.
		
		This method is called automatically when the document is cancelled.
		It handles cleanup of all related records including Payment Entries.
		"""
		try:
			self._cleanup_related_advice_records()
		except Exception as e:
			# Log error but don't prevent cancellation
			frappe.log_error(
				title=f"Error during bulk upload cancellation cleanup for {self.name}",
				message=f"Failed to cleanup related records: {str(e)}\n\n{frappe.get_traceback()}"
			)
			# Show warning but allow cancellation to proceed
			frappe.msgprint(
				_("Warning: Some related records may not have been cleaned up. Please check Error Log."),
				indicator="orange",
				alert=True
			)
	
	def _cleanup_related_advice_records(self):
		"""Cancel and delete all Bank Payment Advice records linked to this bulk upload.
		
		This method:
		- Fetches all advice records via bulk_upload_reference
		- Handles linked Payment Entries (cancels them first if needed)
		- Cancels each advice if submitted
		- Force deletes each record (with child invoice rows)
		- Logs failures but continues execution
		- Commits safely
		"""
		# Fetch all related advice records with payment_entry info
		advice_records = frappe.get_all(
			"Bank Payment Advice",
			filters={"bulk_upload_reference": self.name},
			fields=["name", "docstatus", "payment_entry"],
		)
		
		if not advice_records:
			frappe.logger().info(
				f"No Bank Payment Advice records found for bulk upload {self.name}"
			)
			return
		
		frappe.logger().info(
			f"Cleaning up {len(advice_records)} Bank Payment Advice record(s) for bulk upload {self.name}"
		)
		
		success_count = 0
		failed_count = 0
		failed_records = []
		
		for advice_record in advice_records:
			advice_name = advice_record.name
			payment_entry = advice_record.payment_entry
			
			try:
				# Check if document still exists (idempotency)
				if not frappe.db.exists("Bank Payment Advice", advice_name):
					frappe.logger().info(
						f"Bank Payment Advice {advice_name} already deleted, skipping"
					)
					success_count += 1
					continue
				
				# Get the advice document
				advice_doc = frappe.get_doc("Bank Payment Advice", advice_name)
				
				# Handle linked Payment Entry first (if exists)
				if payment_entry and frappe.db.exists("Payment Entry", payment_entry):
					try:
						pe_doc = frappe.get_doc("Payment Entry", payment_entry)
						# Cancel Payment Entry if submitted
						if pe_doc.docstatus == 1:
							pe_doc.flags.ignore_permissions = True
							pe_doc.cancel()
							frappe.db.commit()
							frappe.logger().info(
								f"Cancelled linked Payment Entry {payment_entry} for advice {advice_name}"
							)
						# Delete Payment Entry
						frappe.delete_doc(
							doctype="Payment Entry",
							name=payment_entry,
							force=True,
							ignore_permissions=True,
						)
						frappe.db.commit()
						frappe.logger().info(
							f"Deleted linked Payment Entry {payment_entry} for advice {advice_name}"
						)
						# Clear the link in advice record
						frappe.db.set_value(
							"Bank Payment Advice",
							advice_name,
							"payment_entry",
							None,
							update_modified=False,
						)
					except Exception as pe_error:
						# Log but continue - we'll try to delete advice anyway
						frappe.log_error(
							title=f"Error handling Payment Entry {payment_entry} for advice {advice_name}",
							message=f"Failed to handle Payment Entry: {str(pe_error)}\n\n{frappe.get_traceback()}"
						)
				
				# Cancel if submitted (docstatus = 1)
				if advice_doc.docstatus == 1:
					try:
						advice_doc.flags.ignore_permissions = True
						advice_doc.cancel()
						frappe.db.commit()
						frappe.logger().info(
							f"Cancelled Bank Payment Advice {advice_name} before deletion"
						)
					except Exception as cancel_error:
						# Log but continue - we'll try to force delete anyway
						frappe.log_error(
							title=f"Error cancelling Bank Payment Advice {advice_name}",
							message=f"Failed to cancel advice {advice_name}: {str(cancel_error)}\n\n{frappe.get_traceback()}"
						)
				
				# Force delete the advice record
				# This will automatically delete child invoice rows
				# Set flag to allow deletion (bypasses on_trash prevention)
				frappe.flags.bulk_cleanup = True
				try:
					frappe.delete_doc(
						doctype="Bank Payment Advice",
						name=advice_name,
						force=True,  # Bypass link checks
						ignore_permissions=True,  # Bypass permission checks
					)
					frappe.db.commit()
				finally:
					# Clear flag after deletion attempt
					frappe.flags.bulk_cleanup = False
				
				success_count += 1
				frappe.logger().info(
					f"Successfully deleted Bank Payment Advice {advice_name}"
				)
				
			except frappe.DoesNotExistError:
				# Document already deleted (race condition or idempotent retry)
				frappe.logger().info(
					f"Bank Payment Advice {advice_name} does not exist, skipping"
				)
				success_count += 1
			except Exception as e:
				failed_count += 1
				failed_records.append(advice_name)
				
				# Log error but continue with other records
				frappe.log_error(
					title=f"Error deleting Bank Payment Advice {advice_name}",
					message=f"Failed to delete advice {advice_name} from bulk upload {self.name}: {str(e)}\n\n{frappe.get_traceback()}"
				)
		
		# Commit all deletions
		try:
			frappe.db.commit()
		except Exception as commit_error:
			frappe.log_error(
				title="Error committing advice deletions",
				message=f"Failed to commit deletions for bulk upload {self.name}: {str(commit_error)}\n\n{frappe.get_traceback()}"
			)
		
		# Log summary
		if failed_count > 0:
			frappe.logger().warning(
				f"Bulk upload {self.name}: Deleted {success_count} advice record(s), "
				f"failed to delete {failed_count} record(s): {', '.join(failed_records)}"
			)
		else:
			frappe.logger().info(
				f"Bulk upload {self.name}: Successfully deleted all {success_count} advice record(s)"
			)
		
		# Show user-friendly message
		if success_count > 0:
			frappe.msgprint(
				_("Deleted {0} related Bank Payment Advice record(s)").format(success_count),
				indicator="green",
				alert=True
			)
		
		if failed_count > 0:
			frappe.msgprint(
				_("Warning: Failed to delete {0} advice record(s). Please check Error Log.").format(failed_count),
				indicator="orange",
				alert=True
			)
