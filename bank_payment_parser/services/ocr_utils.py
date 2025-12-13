"""
OCR Utilities for PDF Text Extraction

Handles both text-based PDFs and scanned PDFs using OCR.
"""

import frappe
import os
from typing import Optional


def extract_text_from_pdf(pdf_path: str, use_ocr: bool = False) -> str:
	"""
	Extract text from PDF file.
	
	First tries pdfminer for text-based PDFs.
	If that fails or returns empty, falls back to OCR if enabled.
	
	Args:
		pdf_path: Path to PDF file
		use_ocr: Whether to use OCR if text extraction fails
	
	Returns:
		Extracted text string
	"""
	try:
		from pdfminer.high_level import extract_text as pdfminer_extract
		
		# Try pdfminer first
		text = pdfminer_extract(pdf_path)
		
		# If text extraction failed or returned empty, try OCR
		if (not text or not text.strip()) and use_ocr:
			frappe.log_error(f"PDF text extraction returned empty, trying OCR for: {pdf_path}")
			text = extract_text_with_ocr(pdf_path)
		
		return text or ""
	except Exception as e:
		frappe.log_error(f"Error extracting text from PDF {pdf_path}: {str(e)}", "PDF Text Extraction Error")
		
		# Fallback to OCR if enabled
		if use_ocr:
			try:
				return extract_text_with_ocr(pdf_path)
			except Exception as ocr_error:
				frappe.log_error(f"OCR also failed for {pdf_path}: {str(ocr_error)}", "OCR Error")
		
		return ""


def extract_text_with_ocr(pdf_path: str) -> str:
	"""
	Extract text from scanned PDF using OCR (Tesseract).
	
	Args:
		pdf_path: Path to PDF file
	
	Returns:
		Extracted text string
	
	Raises:
		ImportError: If required OCR libraries are not installed
		Exception: If OCR processing fails
	"""
	try:
		import pytesseract
		from pdf2image import convert_from_path
		from PIL import Image
	except ImportError:
		error_msg = (
			"OCR libraries not installed. Install with: "
			"pip install pytesseract pdf2image pillow"
		)
		frappe.throw(error_msg)
	
	try:
		# Convert PDF pages to images
		images = convert_from_path(pdf_path)
		
		# Extract text from each image
		extracted_text = ""
		for image in images:
			text = pytesseract.image_to_string(image)
			extracted_text += text + "\n"
		
		return extracted_text.strip()
	except Exception as e:
		error_msg = f"OCR processing failed: {str(e)}"
		frappe.log_error(error_msg, "OCR Processing Error")
		raise


def get_pdf_file_path(file_url: str) -> Optional[str]:
	"""
	Get absolute file path from Frappe file URL.
	
	Args:
		file_url: Frappe file URL (e.g., "/files/document.pdf" or "/private/files/document.pdf")
	
	Returns:
		Absolute file path or None if invalid
	"""
	if not file_url:
		return None
	
	# Handle private files
	if file_url.startswith("/private/files/"):
		file_path = frappe.get_site_path("private", "files", file_url.split("/")[-1])
	# Handle public files
	elif file_url.startswith("/files/"):
		file_path = frappe.get_site_path("public", "files", file_url.split("/")[-1])
	else:
		# Assume it's already an absolute path
		file_path = file_url
	
	# Validate file exists
	if not os.path.exists(file_path):
		frappe.log_error(f"PDF file not found: {file_path}", "File Not Found")
		return None
	
	return file_path
