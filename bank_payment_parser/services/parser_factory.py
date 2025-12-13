"""
Parser Factory

Detects customer from PDF and returns the appropriate parser instance.
"""

import frappe
from typing import Optional, Type
from bank_payment_parser.services.base_parser import BaseParser
from bank_payment_parser.services.hindustan_zinc import HindustanZincParser
from bank_payment_parser.services.generic_parser import GenericParser


# Registry of customer parsers
# Format: "customer_name": ParserClass
PARSER_REGISTRY = {
	"Hindustan Zinc India Ltd": HindustanZincParser,
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
		"HINDUSTAN ZINC": "Hindustan Zinc India Ltd",
		"HZL": "Hindustan Zinc India Ltd",
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


def get_supported_customers() -> list:
	"""
	Get list of supported customer names.
	
	Returns:
		List of customer names that have registered parsers
	"""
	return list(PARSER_REGISTRY.keys())
