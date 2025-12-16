"""
API endpoints for bulk file upload and processing (PDF + XML).
"""

import os

import frappe
from frappe import _
from frappe.utils import now
from bank_payment_parser.jobs.bulk_processor import enqueue_bulk_processing


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
def add_file_to_bulk_upload(bulk_upload_name: str, file_url: str, file_name: str):
	"""
	Add a file to bulk upload items.
	
	Args:
		bulk_upload_name: Name of the bulk upload document
		file_url: URL of the uploaded file
		file_name: Name of the file
	
	Returns:
		Dictionary with success status
	"""
	bulk_upload = frappe.get_doc("Bank Payment Bulk Upload", bulk_upload_name)
	
	# Derive file type from extension
	ext = os.path.splitext(file_name or "")[1].lower()
	if ext == ".pdf":
		file_type = "PDF"
	elif ext == ".xml":
		file_type = "XML"
	else:
		file_type = "Unknown"
	
	bulk_upload.append("items", {
		"pdf_file": file_url,
		"file_name": file_name,
		"file_type": file_type,
		"parse_status": "Pending"
	})
	
	bulk_upload.save(ignore_permissions=True)
	frappe.db.commit()
	
	return {
		"success": True
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
