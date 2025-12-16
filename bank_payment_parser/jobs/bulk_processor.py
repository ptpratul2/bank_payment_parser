"""Background jobs for bulk Bank Payment Advice parsing (PDF + XML)."""
from __future__ import annotations

import os

import frappe
from frappe import _
from frappe.utils.file_manager import get_file

from bank_payment_parser.services.ocr_utils import extract_text_from_pdf, get_pdf_file_path
from bank_payment_parser.services.parser_factory import get_parser_for_file
from bank_payment_parser.services.payment_advice_creator import create_payment_advice_from_parsed_data


def enqueue_bulk_processing(bulk_upload_name: str, reprocess: bool = False):
	"""Enqueue background jobs for all items in a bulk upload.

	Each file is processed in its own job on the ``long`` queue.
	"""
	bulk_upload = frappe.get_doc("Bank Payment Bulk Upload", bulk_upload_name)

	# Decide which items to process
	if reprocess:
		items = [it for it in bulk_upload.items if it.parse_status == "Failed"]
	else:
		items = [it for it in bulk_upload.items if it.parse_status == "Pending"]

	if not items:
		frappe.log_error("No items to process in bulk upload", "Bulk Upload Processing")
		return

	bulk_upload.status = "Processing"
	bulk_upload.save(ignore_permissions=True)
	frappe.db.commit()

	for it in items:
		frappe.enqueue(
			method="bank_payment_parser.jobs.bulk_processor.process_single_pdf",
			queue="long",
			job_name=f"Parse File: {it.file_name or it.name}",
			bulk_upload_name=bulk_upload_name,
			item_name=it.name,
			file_url=it.pdf_file,
			customer=bulk_upload.customer,
			timeout=300,
		)

	frappe.logger().info(
		f"Enqueued {len(items)} file(s) for bulk upload {bulk_upload_name}"
	)


@frappe.whitelist()
def process_single_pdf(
	bulk_upload_name: str,
	item_name: str,
	file_url: str,
	customer: str | None = None,
):
	"""Process a single bulk-uploaded file (PDF or XML).

	The name is kept for backward compatibility with existing jobs.
	"""
	# We deliberately keep the logic straightforward so that any
	# exceptions are easy to see in the worker logs and console.
	item = frappe.get_doc("Bank Payment Bulk Upload Item", item_name)

	if not file_url:
		raise ValueError("File URL is required")

	# Detect file type from extension
	ext = os.path.splitext(file_url or "")[1].lower()

	# Load raw payload
	if ext == ".pdf":
		pdf_path = get_pdf_file_path(file_url)
		if not pdf_path:
			raise ValueError(f"PDF file not found: {file_url}")

		raw_payload = extract_text_from_pdf(pdf_path, use_ocr=False)
		if not raw_payload or not raw_payload.strip():
			# Fallback to OCR
			raw_payload = extract_text_from_pdf(pdf_path, use_ocr=True)
			if not raw_payload or not raw_payload.strip():
				raise ValueError("Could not extract text from PDF")
		file_type = "PDF"
	elif ext == ".xml":
		file_doc, content = get_file(file_url)
		if isinstance(content, bytes):
			raw_payload = content.decode("utf-8", errors="ignore")
		else:
			raw_payload = content or ""
		file_type = "XML"
	else:
		raise ValueError(f"Unsupported file type: {ext or 'unknown'}")

	# Route to appropriate parser
	parser = get_parser_for_file(
		file_url=file_url,
		raw_payload=raw_payload,
		user_selected_customer=customer,
	)

	parsed_data = parser.parse()

	# Create Bank Payment Advice using centralized service
	payment_advice = create_payment_advice_from_parsed_data(
		parsed_data=parsed_data,
		file_url=file_url,
		file_type=file_type,
		customer=customer,
		bulk_upload_reference=bulk_upload_name,
	)
	
	# Save the document
	payment_advice.insert(ignore_permissions=True)
	frappe.db.commit()

	# Mark child item as success directly in DB (works even when parent is submitted)
	frappe.db.set_value(
		"Bank Payment Bulk Upload Item",
		item_name,
		{
			"parse_status": "Success",
			"parsed_document": payment_advice.name,
			"parser_used": parsed_data.get("parser_used", "Unknown"),
			"error_message": "",
		},
	)
	frappe.db.commit()

	# Update parent roll-up status
	bulk_upload = frappe.get_doc("Bank Payment Bulk Upload", bulk_upload_name)
	bulk_upload.update_status()

	frappe.logger().info(
		f"Successfully processed file {item.file_name} ({file_type}) from bulk upload {bulk_upload_name}"
	)
