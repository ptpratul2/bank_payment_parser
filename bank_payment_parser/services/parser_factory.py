"""
Parser Factory

Detects customer from content and returns the appropriate parser instance.

This module now supports both:
- PDF parsers (customer-wise)
- XML (cXML PaymentRemittanceRequest) parsers
"""

import os
from typing import Optional, Type, List

import frappe

from bank_payment_parser.services.base_parser import BaseParser
from bank_payment_parser.services.hindustan_zinc import HindustanZincParser
from bank_payment_parser.services.generic_parser import GenericParser
from bank_payment_parser.services.pdf.hindustan_zinc_pdf import HindustanZincPDFParser
from bank_payment_parser.services.pdf.generic_pdf import GenericPDFParser
from bank_payment_parser.services.xml.cxml_payment_remittance import CXMLPaymentRemittanceParser


# Legacy registry of customer parsers (PDF only, kept for backward compatibility)
PARSER_REGISTRY = {
	"Hindustan Zinc India Ltd": HindustanZincParser,
	"Hindustan Zinc India Limited": HindustanZincParser,
	"Hindustan Zinc": HindustanZincParser,
	"HZL": HindustanZincParser,
	# Add more customer parsers here as they are implemented
}


def detect_customer_from_text(text: str) -> Optional[str]:
	"""
	Detect customer/paying company from PDF text using keywords.
	
	Args:
		text: Extracted PDF text
	
	Returns:
		Customer name if detected, None otherwise
	"""
	if not text:
		return None
	
	text_upper = text.upper()
	
	# Check each registered customer
	for customer_name, parser_class in PARSER_REGISTRY.items():
		# Check if customer name appears in text
		if customer_name.upper() in text_upper:
			return customer_name
	
	# Check for common variations
	customer_keywords = {
		"HINDUSTAN ZINC": "Hindustan Zinc India Limited",
		"HZL": "Hindustan Zinc India Limited",
		# Add more keyword mappings here
	}
	
	for keyword, customer_name in customer_keywords.items():
		if keyword in text_upper:
			return customer_name
	
	return None


def get_parser(
	customer_name: Optional[str] = None,
	pdf_path: str = "",
	raw_text: str = "",
	user_selected_customer: Optional[str] = None
) -> BaseParser:
	"""
	Get the appropriate parser instance for a customer.
	
	Priority:
	1. User-selected customer (if provided)
	2. Detected customer from PDF text
	3. Generic parser as fallback
	
	Args:
		customer_name: Explicit customer name (deprecated, use user_selected_customer)
		pdf_path: Path to PDF file
		raw_text: Extracted PDF text
		user_selected_customer: Customer selected by user during upload
	
	Returns:
		Parser instance (BaseParser subclass)
	"""
	# Priority 1: User-selected customer
	selected_customer = user_selected_customer or customer_name
	
	# Priority 2: Auto-detect from PDF text
	if not selected_customer and raw_text:
		selected_customer = detect_customer_from_text(raw_text)
	
	# Priority 3: Fallback to generic parser
	if not selected_customer:
		frappe.log_error(
			f"Could not detect customer. Using generic parser for: {pdf_path}",
			"Customer Detection Failed"
		)
		return GenericParser(pdf_path, raw_text, "Unknown")
	
	# Get parser class from registry
	parser_class = PARSER_REGISTRY.get(selected_customer)
	
	if not parser_class:
		# Customer detected but no parser registered
		frappe.log_error(
			f"Customer '{selected_customer}' detected but no parser registered. Using generic parser.",
			"Parser Not Found"
		)
		return GenericParser(pdf_path, raw_text, selected_customer)
	
	# Return parser instance
	try:
		return parser_class(pdf_path, raw_text, selected_customer)
	except Exception as e:
		frappe.log_error(
			f"Error instantiating parser for '{selected_customer}': {str(e)}",
			"Parser Instantiation Error"
		)
		return GenericParser(pdf_path, raw_text, selected_customer)


def register_parser(customer_name: str, parser_class: Type[BaseParser]):
	"""
	Register a new customer parser.
	
	This allows dynamic registration of parsers without modifying this file.
	
	Args:
		customer_name: Name of the customer (must match exactly)
		parser_class: Parser class (must inherit from BaseParser)
	
	Example:
		from bank_payment_parser.services.parser_factory import register_parser
		from bank_payment_parser.services.my_customer_parser import MyCustomerParser
		
		register_parser("My Customer Ltd", MyCustomerParser)
	"""
	if not issubclass(parser_class, BaseParser):
		raise ValueError(f"Parser class must inherit from BaseParser")
	
	PARSER_REGISTRY[customer_name] = parser_class
	frappe.log_error(f"Registered parser for customer: {customer_name}", "Parser Registration")


def get_supported_customers() -> List[str]:
	"""
	Get list of supported customer names.
	
	Returns:
		List of customer names that have registered parsers
	"""
	return list(PARSER_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Unified factory for file-type aware parsing (PDF + XML)
# ---------------------------------------------------------------------------

PDF_REGISTRY: dict[str, Type[BaseParser]] = {
	"Hindustan Zinc India Ltd": HindustanZincPDFParser,
	"Hindustan Zinc India Limited": HindustanZincPDFParser,
	"Hindustan Zinc": HindustanZincPDFParser,
	"HZL": HindustanZincPDFParser,
}


def _get_file_extension(file_url: str) -> str:
	"""Return lower-case file extension including dot (e.g. '.pdf')."""
	return os.path.splitext(file_url or "")[1].lower()


def get_pdf_parser_class(customer: Optional[str]) -> Type[BaseParser]:
	"""Return PDF parser class for given customer, or generic as fallback."""
	if customer and customer in PDF_REGISTRY:
		return PDF_REGISTRY[customer]
	return GenericPDFParser


def get_xml_parser_class(customer: Optional[str]) -> Type[BaseParser]:
	"""Return XML parser class. Currently customer-agnostic."""
	# In future, you can switch on customer here
	return CXMLPaymentRemittanceParser


def get_parser_for_file(
	file_url: str,
	raw_payload: str,
	user_selected_customer: Optional[str] = None,
) -> BaseParser:
	"""
	Unified entry: choose parser based on file extension.

	- PDF -> customer-wise PDF parser (Hindustan Zinc or generic)
	- XML -> cXML PaymentRemittanceRequest parser
	"""
	ext = _get_file_extension(file_url)
	customer = user_selected_customer

	if ext == ".pdf":
		ParserCls = get_pdf_parser_class(customer)
		# For compatibility with existing BaseParser signature
		return ParserCls(file_url, raw_payload, customer or "Unknown")

	if ext == ".xml":
		ParserCls = get_xml_parser_class(customer)
		return ParserCls(xml_text=raw_payload, customer_name=customer)

	# Unsupported type
	raise frappe.ValidationError(f"Unsupported file type for parsing: {ext or 'unknown'}")
