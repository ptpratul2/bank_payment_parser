"""
Base Parser Abstract Class

All customer-specific parsers must inherit from this class and implement
the parse() method.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import frappe


class BaseParser(ABC):
	"""
	Abstract base class for all customer-specific payment advice parsers.
	
	Each customer parser must:
	1. Inherit from this class
	2. Implement the parse() method
	3. Return a standardized dictionary with extracted fields
	"""
	
	def __init__(self, pdf_path: str, raw_text: str, customer_name: str):
		"""
		Initialize the parser.
		
		Args:
			pdf_path: Path to the PDF file
			raw_text: Extracted text from PDF
			customer_name: Name of the customer/paying company
		"""
		self.pdf_path = pdf_path
		self.raw_text = raw_text
		self.customer_name = customer_name
		self.parse_version = "1.0"
	
	@abstractmethod
	def parse(self) -> Dict[str, Any]:
		"""
		Parse the payment advice PDF and extract fields.
		
		Returns:
			Dictionary with standardized fields:
			{
				"customer_name": str,
				"payment_document_no": str,
				"payment_date": str (YYYY-MM-DD),
				"bank_reference_no": str,
				"utr_rrn_no": str,
				"invoice_no": str or list,
				"invoice_date": str or list,
				"payment_amount": float,
				"beneficiary_name": str,
				"beneficiary_account_no": str,
				"bank_name": str,
				"currency": str (default: "INR"),
				"remarks": str,
				"raw_text": str,
				"parser_used": str,
				"parse_version": str
			}
		
		Raises:
			ValueError: If required fields cannot be extracted
		"""
		pass
	
	def normalize_date(self, date_str: str) -> Optional[str]:
		"""
		Normalize various date formats to YYYY-MM-DD.
		
		Supports:
		- DD.MM.YYYY (e.g., 03.12.2025)
		- DD/MM/YYYY (e.g., 07/11/2025)
		- DD-MM-YYYY
		- YYYY-MM-DD (already normalized)
		
		Args:
			date_str: Date string in various formats
		
		Returns:
			Normalized date string (YYYY-MM-DD) or None if invalid
		"""
		if not date_str:
			return None
		
		import re
		from datetime import datetime
		
		# Remove extra whitespace
		date_str = date_str.strip()
		
		# Try different formats
		formats = [
			"%d.%m.%Y",  # 03.12.2025
			"%d/%m/%Y",  # 07/11/2025
			"%d-%m-%Y",  # 07-11-2025
			"%Y-%m-%d",  # 2025-12-03 (already normalized)
		]
		
		for fmt in formats:
			try:
				dt = datetime.strptime(date_str, fmt)
				return dt.strftime("%Y-%m-%d")
			except ValueError:
				continue
		
		# Try regex-based extraction for malformed dates
		date_patterns = [
			r"(\d{2})\.(\d{2})\.(\d{4})",  # DD.MM.YYYY
			r"(\d{2})/(\d{2})/(\d{4})",   # DD/MM/YYYY
			r"(\d{2})-(\d{2})-(\d{4})",   # DD-MM-YYYY
		]
		
		for pattern in date_patterns:
			match = re.search(pattern, date_str)
			if match:
				day, month, year = match.groups()
				try:
					dt = datetime(int(year), int(month), int(day))
					return dt.strftime("%Y-%m-%d")
				except ValueError:
					continue
		
		frappe.log_error(f"Could not parse date: {date_str}", "Date Parsing Error")
		return None
	
	def normalize_amount(self, amount_str: str) -> float:
		"""
		Normalize amount string to float.
		
		Removes currency symbols, commas, and whitespace.
		
		Args:
			amount_str: Amount string (e.g., "₹1,23,456.78" or "123456.78")
		
		Returns:
			Float value or 0.0 if invalid
		"""
		if not amount_str:
			return 0.0
		
		import re
		
		# Remove currency symbols, commas, and whitespace
		cleaned = re.sub(r'[₹$€£,\s]', '', str(amount_str))
		
		try:
			return float(cleaned)
		except ValueError:
			frappe.log_error(f"Could not parse amount: {amount_str}", "Amount Parsing Error")
			return 0.0
	
	def extract_by_keyword(self, keyword: str, case_sensitive: bool = False) -> Optional[str]:
		"""
		Extract value after a keyword in the text.
		
		Args:
			keyword: Keyword to search for
			case_sensitive: Whether search should be case-sensitive
		
		Returns:
			Extracted value or None
		"""
		import re
		
		flags = 0 if case_sensitive else re.IGNORECASE
		pattern = rf"{re.escape(keyword)}\s*[:=]?\s*([^\n\r]+)"
		
		match = re.search(pattern, self.raw_text, flags)
		if match:
			return match.group(1).strip()
		
		return None
	
	def extract_multiple_by_keyword(self, keyword: str, case_sensitive: bool = False) -> list:
		"""
		Extract all values after a keyword (for multiple occurrences).
		
		Args:
			keyword: Keyword to search for
			case_sensitive: Whether search should be case-sensitive
		
		Returns:
			List of extracted values
		"""
		import re
		
		flags = 0 if case_sensitive else re.IGNORECASE
		pattern = rf"{re.escape(keyword)}\s*[:=]?\s*([^\n\r]+)"
		
		matches = re.findall(pattern, self.raw_text, flags)
		return [m.strip() for m in matches if m.strip()]
