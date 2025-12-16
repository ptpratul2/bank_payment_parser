"""
API endpoints for uploading and parsing bank payment advice PDFs.
"""

import frappe
from frappe import _
from frappe.utils import now
from bank_payment_parser.services.parser_factory import get_parser
from bank_payment_parser.services.ocr_utils import extract_text_from_pdf, get_pdf_file_path
from bank_payment_parser.services.payment_advice_creator import create_payment_advice_from_parsed_data


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
	
	# Create Bank Payment Advice using centralized service
	doc = create_payment_advice_from_parsed_data(
		parsed_data=parsed_data,
		file_url=file_url,
		file_type="PDF",
		customer=customer,
		bulk_upload_reference=None,
	)
	
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
