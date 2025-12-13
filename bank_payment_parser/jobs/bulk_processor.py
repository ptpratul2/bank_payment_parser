"""
Background job handlers for bulk PDF processing
"""

import frappe
from frappe import _
from frappe.utils import now
from bank_payment_parser.api.upload import create_payment_advice
from bank_payment_parser.services.parser_factory import get_parser
from bank_payment_parser.services.ocr_utils import extract_text_from_pdf, get_pdf_file_path


def enqueue_bulk_processing(bulk_upload_name: str, reprocess: bool = False):
	"""
	Enqueue background jobs for processing all items in bulk upload.
	Each PDF is processed in a separate job.
	
	Args:
		bulk_upload_name: Name of the Bank Payment Bulk Upload document
		reprocess: If True, only process failed items
	"""
	# Get bulk upload document
	bulk_upload = frappe.get_doc("Bank Payment Bulk Upload", bulk_upload_name)
	
	# Determine which items to process
	if reprocess:
		items_to_process = [item for item in bulk_upload.items if item.parse_status == "Failed"]
	else:
		items_to_process = [item for item in bulk_upload.items if item.parse_status == "Pending"]
	
	if not items_to_process:
		frappe.log_error(
			"No items to process in bulk upload",
			"Bulk Upload Processing"
		)
		return
	
	# Update status to Processing
	bulk_upload.status = "Processing"
	bulk_upload.save(ignore_permissions=True)
	frappe.db.commit()
	
	# Enqueue individual jobs for each PDF
	for item in items_to_process:
		frappe.enqueue(
			method="bank_payment_parser.jobs.bulk_processor.process_single_pdf",
			queue="long",
			job_name=f"Parse PDF: {item.file_name or item.name}",
			timeout=300,  # 5 minutes per file
			kwargs={
				"bulk_upload_name": bulk_upload_name,
				"item_name": item.name,
				"file_url": item.pdf_file,
				"customer": bulk_upload.customer
			}
		)
	
	frappe.logger().info(
		f"Enqueued {len(items_to_process)} PDF processing jobs for bulk upload {bulk_upload_name}"
	)


@frappe.whitelist()
def process_single_pdf(bulk_upload_name: str, item_name: str, file_url: str, customer: str = None):
	"""
	Process a single PDF from bulk upload.
	This is called as a background job.
	
	Args:
		bulk_upload_name: Name of the Bank Payment Bulk Upload document
		item_name: Name of the Bank Payment Bulk Upload Item
		file_url: URL of the PDF file
		customer: Customer name (optional, will auto-detect if not provided)
	
	Returns:
		None (updates child item directly)
	"""
	try:
		# Get the child item
		item = frappe.get_doc("Bank Payment Bulk Upload Item", item_name)
		
		# Validate file exists
		if not file_url:
			raise ValueError("File URL is required")
		
		# Get PDF path
		pdf_path = get_pdf_file_path(file_url)
		if not pdf_path:
			raise ValueError(f"PDF file not found: {file_url}")
		
		# Extract text from PDF
		raw_text = extract_text_from_pdf(pdf_path, use_ocr=False)
		if not raw_text or not raw_text.strip():
			# Try with OCR if text extraction fails
			raw_text = extract_text_from_pdf(pdf_path, use_ocr=True)
			if not raw_text or not raw_text.strip():
				raise ValueError("Could not extract text from PDF")
		
		# Get parser (reuse existing logic)
		parser = get_parser(
			pdf_path=pdf_path,
			raw_text=raw_text,
			user_selected_customer=customer
		)
		
		# Parse PDF (reuse existing logic)
		parsed_data = parser.parse()
		
		# Create Bank Payment Advice document (reuse existing logic)
		payment_advice_doc = frappe.get_doc({
			"doctype": "Bank Payment Advice",
			"customer": customer or parsed_data.get("customer_name"),
			"payment_document_no": parsed_data.get("payment_document_no"),
			"payment_date": parsed_data.get("payment_date"),
			"bank_reference_no": parsed_data.get("bank_reference_no"),
			"utr_rrn_no": parsed_data.get("utr_rrn_no"),
			"payment_amount": parsed_data.get("payment_amount", 0),
			"beneficiary_name": parsed_data.get("beneficiary_name"),
			"beneficiary_account_no": parsed_data.get("beneficiary_account_no"),
			"bank_name": parsed_data.get("bank_name"),
			"currency": parsed_data.get("currency", "INR"),
			"remarks": parsed_data.get("remarks"),
			"pdf_file": file_url,
			"raw_text": parsed_data.get("raw_text"),
			"parser_used": parsed_data.get("parser_used"),
			"parse_version": parsed_data.get("parse_version"),
			"parse_status": "Parsed"
		})
		
		# Add invoice details if available
		invoice_table_data = parsed_data.get("invoice_table_data", [])
		total_amount = parsed_data.get("payment_amount", 0)
		
		if invoice_table_data:
			amount_per_invoice = total_amount / len(invoice_table_data) if len(invoice_table_data) > 0 else 0
			
			for invoice_row in invoice_table_data:
				if invoice_row.get("invoice_number_pf"):
					payment_advice_doc.append("invoices", {
						"invoice_number_pf": invoice_row.get("invoice_number_pf", ""),
						"invoice_date_advanced_adjusted": invoice_row.get("invoice_date_advanced_adjusted", ""),
						"tds_wct": invoice_row.get("tds_wct", 0.0),
						"other_deductions_security_retention": invoice_row.get("other_deductions_security_retention", 0.0),
						"amount": amount_per_invoice
					})
		
		# Save payment advice
		payment_advice_doc.insert(ignore_permissions=True)
		frappe.db.commit()
		
		# Update child item with success
		item.parse_status = "Success"
		item.parsed_document = payment_advice_doc.name
		item.parser_used = parsed_data.get("parser_used", "Unknown")
		item.error_message = ""
		item.save(ignore_permissions=True)
		frappe.db.commit()
		
		# Update parent status
		bulk_upload = frappe.get_doc("Bank Payment Bulk Upload", bulk_upload_name)
		bulk_upload.update_status()
		
		frappe.logger().info(
			f"Successfully processed PDF {item.file_name} from bulk upload {bulk_upload_name}"
		)
		
	except Exception as e:
		# Capture error and update child item
		error_message = str(e)
		traceback_str = frappe.get_traceback()
		
		# Log error
		frappe.log_error(
			title="Bulk Upload Processing Error",
			message=f"Error processing PDF {item_name}: {error_message}\n\n{traceback_str}"
		)
		
		# Update child item with failure
		try:
			item = frappe.get_doc("Bank Payment Bulk Upload Item", item_name)
			item.parse_status = "Failed"
			item.error_message = error_message[:500]  # Limit error message length
			item.parsed_document = ""
			item.save(ignore_permissions=True)
			frappe.db.commit()
			
			# Update parent status
			bulk_upload = frappe.get_doc("Bank Payment Bulk Upload", bulk_upload_name)
			bulk_upload.update_status()
		except Exception as update_error:
			frappe.log_error(
				message=f"Error updating item status: {str(update_error)}",
				title="Bulk Upload Status Update Error"
			)
