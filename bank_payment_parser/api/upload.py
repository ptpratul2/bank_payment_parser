"""
API endpoints for uploading and parsing bank payment advice PDFs.
"""

import frappe
from frappe import _
from frappe.utils import now
from bank_payment_parser.services.parser_factory import get_parser
from bank_payment_parser.services.ocr_utils import extract_text_from_pdf, get_pdf_file_path


@frappe.whitelist()
def upload_and_parse(file_url: str, customer: str = None, use_ocr: bool = False):
	"""
	Upload and parse a bank payment advice PDF.
	
	Args:
		file_url: URL of the uploaded PDF file
		customer: Customer name (optional, will auto-detect if not provided)
		use_ocr: Whether to use OCR if text extraction fails
	
	Returns:
		Dictionary with parsing results
	"""
	if not file_url:
		frappe.throw(_("File URL is required"))
	
	# Get file path
	pdf_path = get_pdf_file_path(file_url)
	if not pdf_path:
		frappe.throw(_("PDF file not found"))
	
	# Extract text from PDF
	try:
		raw_text = extract_text_from_pdf(pdf_path, use_ocr=use_ocr)
		if not raw_text or not raw_text.strip():
			frappe.throw(_("Could not extract text from PDF. Please ensure the PDF contains text or enable OCR."))
	except Exception as e:
		frappe.log_error(f"Text extraction failed: {str(e)}", "PDF Text Extraction")
		frappe.throw(_(f"Error extracting text from PDF: {str(e)}"))
	
	# Get parser
	try:
		parser = get_parser(
			pdf_path=pdf_path,
			raw_text=raw_text,
			user_selected_customer=customer
		)
	except Exception as e:
		frappe.log_error(f"Parser initialization failed: {str(e)}", "Parser Initialization")
		frappe.throw(_(f"Error initializing parser: {str(e)}"))
	
	# Parse PDF
	try:
		parsed_data = parser.parse()
	except Exception as e:
		frappe.log_error(f"Parsing failed: {str(e)}", "PDF Parsing Error")
		frappe.throw(_(f"Error parsing PDF: {str(e)}"))
	
	return {
		"success": True,
		"parsed_data": parsed_data,
		"parser_used": parsed_data.get("parser_used"),
		"customer_detected": parsed_data.get("customer_name")
	}


@frappe.whitelist()
def create_payment_advice(file_url: str, customer: str = None, use_ocr: bool = False):
	"""
	Upload, parse, and create a Bank Payment Advice document.
	
	This method is called from the UI after file upload.
	
	Args:
		file_url: URL of the uploaded PDF file
		customer: Customer name (optional)
		use_ocr: Whether to use OCR
	
	Returns:
		Dictionary with created document name
	"""
	# Parse the PDF
	parse_result = upload_and_parse(file_url, customer, use_ocr)
	parsed_data = parse_result["parsed_data"]
	
	# Create Bank Payment Advice document
	doc = frappe.get_doc({
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
	# First try to use structured invoice table data (with amounts)
	invoice_table_data = parsed_data.get("invoice_table_data", [])
	total_amount = parsed_data.get("payment_amount", 0)
	
	if invoice_table_data:
		# Use structured data from parser (includes all columns)
		# Calculate amount per invoice: Total Payment Amount / Number of Invoices
		# This matches the PDF format where amount is the payment amount divided equally
		amount_per_invoice = total_amount / len(invoice_table_data) if len(invoice_table_data) > 0 else 0
		
		for invoice_row in invoice_table_data:
			if invoice_row.get("invoice_number"):
				doc.append("invoices", {
					"invoice_number": invoice_row.get("invoice_number"),
					"invoice_date": invoice_row.get("invoice_date"),
					"tds": invoice_row.get("tds", 0.0),
					"other_deductions": invoice_row.get("other_deductions", 0.0),
					"pf": invoice_row.get("pf", 0.0),
					"advanced_adjusted": invoice_row.get("advanced_adjusted", 0.0),
					"wct": invoice_row.get("wct", 0.0),
					"security_retention": invoice_row.get("security_retention", 0.0),
					"amount": amount_per_invoice  # Total payment amount divided equally
				})
	else:
		# Fallback to simple list extraction
		invoice_nos = parsed_data.get("invoice_no", [])
		invoice_dates = parsed_data.get("invoice_date", [])
		
		# Normalize invoice_nos to list
		if invoice_nos:
			if isinstance(invoice_nos, str):
				invoice_nos = [invoice_nos]
			elif not isinstance(invoice_nos, list):
				invoice_nos = []
		
		# Normalize invoice_dates to list
		if invoice_dates:
			if isinstance(invoice_dates, str):
				invoice_dates = [invoice_dates]
			elif not isinstance(invoice_dates, list):
				invoice_dates = []
		
		if invoice_nos:
			total_amount = parsed_data.get("payment_amount", 0)
			amount_per_invoice = total_amount / len(invoice_nos) if len(invoice_nos) > 0 else 0
			
			for idx, invoice_no in enumerate(invoice_nos):
				if invoice_no:  # Skip empty invoice numbers
					doc.append("invoices", {
						"invoice_number": invoice_no,
						"invoice_date": invoice_dates[idx] if idx < len(invoice_dates) and invoice_dates[idx] else None,
						"amount": amount_per_invoice
					})
	
	# Save document
	try:
		doc.insert()
		frappe.db.commit()
		
		return {
			"success": True,
			"name": doc.name,
			"parser_used": parsed_data.get("parser_used"),
			"message": _("Payment Advice created successfully")
		}
	except frappe.DuplicateEntryError:
		frappe.throw(_("A payment advice with this UTR/RRN or Bank Reference already exists"))
	except Exception as e:
		frappe.log_error(f"Error creating payment advice: {str(e)}", "Payment Advice Creation")
		frappe.throw(_(f"Error creating payment advice: {str(e)}"))


@frappe.whitelist()
def parse_in_background(file_url: str, customer: str = None, use_ocr: bool = False):
	"""
	Parse PDF in background job (non-blocking).
	
	Args:
		file_url: URL of the uploaded PDF file
		customer: Customer name (optional)
		use_ocr: Whether to use OCR
	
	Returns:
		Job ID for tracking
	"""
	job = frappe.enqueue(
		"bank_payment_parser.api.upload.create_payment_advice",
		file_url=file_url,
		customer=customer,
		use_ocr=use_ocr,
		queue="default",
		timeout=300
	)
	
	return {
		"success": True,
		"job_id": job.id if hasattr(job, 'id') else None,
		"message": _("Parsing started in background")
	}


@frappe.whitelist()
def get_supported_customers():
	"""
	Get list of supported customers.
	
	Returns:
		List of customer names with registered parsers
	"""
	from bank_payment_parser.services.parser_factory import get_supported_customers
	
	return {
		"customers": get_supported_customers()
	}
