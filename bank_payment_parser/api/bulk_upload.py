"""
API endpoints for bulk file upload and processing (PDF + XML).
"""

import os

import frappe
from frappe import _
from frappe.utils import now, cint
from bank_payment_parser.jobs.bulk_processor import enqueue_bulk_processing


@frappe.whitelist()
def upload_bulk_files(bulk_upload_name: str):
	"""
	Upload multiple PDF/XML files for bulk processing.
	
	This is the ONLY method JS should call for file uploads.
	It handles:
	- File validation (PDF/XML only)
	- File document creation (bypasses MIME type restrictions)
	- Bulk Upload Item creation
	- Proper attachment linking
	- Counter updates
	
	Files are sent via frappe.request.files with key "files" (multiple files).
	
	Args:
		bulk_upload_name: Name of the Bank Payment Bulk Upload document
		
	Returns:
		Dictionary with:
		- success: bool
		- uploaded_count: int
		- failed_count: int
		- errors: list of error messages
	"""
	if not bulk_upload_name:
		frappe.throw(_("Bulk upload name is required"))
	
	# Verify bulk upload exists
	if not frappe.db.exists("Bank Payment Bulk Upload", bulk_upload_name):
		frappe.throw(_("Bulk upload '{0}' not found").format(bulk_upload_name))
	
	bulk_upload = frappe.get_doc("Bank Payment Bulk Upload", bulk_upload_name)
	
	# Get files from request - handle both single "file" and multiple "files"
	files_list = []
	if "files" in frappe.request.files:
		# Multiple files (getlist returns list even for single file)
		files_list = frappe.request.files.getlist("files")
	elif "file" in frappe.request.files:
		# Single file
		files_list = [frappe.request.files["file"]]
	
	if not files_list:
		frappe.throw(_("No files found in request"))
	
	uploaded_count = 0
	failed_count = 0
	errors = []
	
	for file_storage in files_list:
		filename = None
		try:
			# Read file content
			content = file_storage.stream.read()
			filename = file_storage.filename
			
			if not filename:
				errors.append(_("File with no name skipped"))
				failed_count += 1
				continue
			
			# Validate file extension
			ext = os.path.splitext(filename)[1].lower()
			if ext not in [".pdf", ".xml"]:
				errors.append(_("File '{0}' skipped: Only PDF and XML files are allowed").format(filename))
				failed_count += 1
				continue
			
			# Determine file type
			file_type = "PDF" if ext == ".pdf" else "XML"
			
			# Create File document (bypasses MIME type restrictions)
			# Note: We create the file first, then link it to the item
			# The item doesn't exist yet, so we'll attach it later via file_url
			file_doc = frappe.get_doc({
				"doctype": "File",
				"attached_to_doctype": "Bank Payment Bulk Upload Item",
				"attached_to_name": "",  # Item doesn't exist yet, will be linked via file_url
				"attached_to_field": "pdf_file",
				"folder": "Home",
				"file_name": filename,
				"is_private": 1,
				"content": content,
			})
			file_doc.save(ignore_permissions=True)
			
			# Create Bulk Upload Item with file URL
			bulk_upload.append("items", {
				"pdf_file": file_doc.file_url,
				"file_name": filename,
				"file_type": file_type,
				"parse_status": "Pending"
			})
			
			uploaded_count += 1
			
		except Exception as e:
			failed_count += 1
			error_msg = _("Error uploading '{0}': {1}").format(filename or "unknown file", str(e))
			errors.append(error_msg)
			frappe.log_error(
				title="Error uploading file in bulk",
				message=f"File: {filename or 'unknown'}\nError: {str(e)}\n\n{frappe.get_traceback()}"
			)
	
	# Update bulk upload document
	try:
		bulk_upload.total_files = len(bulk_upload.items)
		bulk_upload.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(
			title="Error saving bulk upload",
			message=f"Bulk upload: {bulk_upload_name}\nError: {str(e)}\n\n{frappe.get_traceback()}"
		)
		raise
	
	return {
		"success": True,
		"uploaded_count": uploaded_count,
		"failed_count": failed_count,
		"errors": errors
	}


@frappe.whitelist()
def create_bulk_upload(customer: str, files: list):
	"""
	Create a new bulk upload record.
	
	Args:
		customer: Customer name
		files: List of file metadata (name, size, type)
	
	Returns:
		Dictionary with bulk upload name
	"""
	if not customer:
		frappe.throw(_("Customer is required"))
	
	if not files or len(files) == 0:
		frappe.throw(_("Please select at least one file"))
	
	# Create bulk upload document
	bulk_upload = frappe.get_doc({
		"doctype": "Bank Payment Bulk Upload",
		"customer": customer,
		"total_files": len(files),
		"processed_files": 0,
		"success_count": 0,
		"failed_count": 0,
		"status": "Queued",
		"uploaded_by": frappe.session.user,
		"upload_time": now(),
		"remarks": f"Bulk upload of {len(files)} file(s)"
	})
	
	bulk_upload.insert(ignore_permissions=True)
	frappe.db.commit()
	
	return {
		"success": True,
		"bulk_upload_name": bulk_upload.name
	}




@frappe.whitelist()
def reprocess_failed(bulk_upload_name: str):
	"""
	Reprocess all failed items in bulk upload.
	
	Args:
		bulk_upload_name: Name of the bulk upload document
	
	Returns:
		Dictionary with success status
	"""
	bulk_upload = frappe.get_doc("Bank Payment Bulk Upload", bulk_upload_name)
	bulk_upload.reprocess_failed()
	
	return {
		"success": True,
		"message": _("Reprocessing queued")
	}


@frappe.whitelist()
def get_bulk_upload_status(bulk_upload_name: str):
	"""
	Get current status of bulk upload.
	
	Args:
		bulk_upload_name: Name of the bulk upload document
	
	Returns:
		Dictionary with status information
	"""
	bulk_upload = frappe.get_doc("Bank Payment Bulk Upload", bulk_upload_name)
	
	return {
		"status": bulk_upload.status,
		"total_files": bulk_upload.total_files,
		"processed_files": bulk_upload.processed_files,
		"success_count": bulk_upload.success_count,
		"failed_count": bulk_upload.failed_count
	}
