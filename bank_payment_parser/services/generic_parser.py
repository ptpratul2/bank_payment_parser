"""
Generic Payment Advice Parser

Fallback parser for unsupported customer formats.
Uses basic pattern matching to extract common fields.
"""

from typing import Dict, Any, Optional, List
from bank_payment_parser.services.base_parser import BaseParser
import frappe
import re


class GenericParser(BaseParser):
	"""
	Generic parser for payment advice PDFs.
	
	This is a fallback parser that uses basic pattern matching
	to extract common fields from any payment advice format.
	"""
	
	def parse(self) -> Dict[str, Any]:
		"""
		Parse payment advice using generic patterns.
		
		Returns:
			Dictionary with extracted fields (may be incomplete)
		"""
		result = {
			"customer_name": self.customer_name,
			"payment_document_no": self._extract_generic_document_no(),
			"payment_date": self._extract_generic_date(),
			"bank_reference_no": self._extract_generic_reference(),
			"utr_rrn_no": self._extract_generic_utr(),
			"invoice_no": self._extract_generic_invoice(),
			"invoice_date": [],
			"payment_amount": self._extract_generic_amount(),
			"beneficiary_name": self._extract_generic_beneficiary(),
			"beneficiary_account_no": self._extract_generic_account(),
			"bank_name": None,
			"currency": self._extract_currency(),
			"remarks": None,
			"raw_text": self.raw_text,
			"parser_used": "GenericParser",
			"parse_version": self.parse_version
		}
		
		return result
	
	def _extract_generic_document_no(self) -> Optional[str]:
		"""Extract any document/reference number."""
		patterns = [
			r"(?:Document|Ref|Reference|Advice)\s+No[\.:]?\s*([A-Z0-9\-]+)",
			r"No[\.:]?\s*([A-Z0-9]{8,})",
		]
		
		for pattern in patterns:
			match = re.search(pattern, self.raw_text, re.IGNORECASE)
			if match:
				return match.group(1).strip()
		
		return None
	
	def _extract_generic_date(self) -> Optional[str]:
		"""Extract any date that looks like payment date."""
		patterns = [
			r"(?:Date|Payment\s+Date)[\.:]?\s*(\d{1,2}[\./\-]\d{1,2}[\./\-]\d{2,4})",
		]
		
		for pattern in patterns:
			match = re.search(pattern, self.raw_text, re.IGNORECASE)
			if match:
				normalized = self.normalize_date(match.group(1))
				if normalized:
					return normalized
		
		return None
	
	def _extract_generic_reference(self) -> Optional[str]:
		"""Extract any reference number."""
		patterns = [
			r"(?:Ref|Reference)\s+No[\.:]?\s*([A-Z0-9\-]+)",
		]
		
		for pattern in patterns:
			match = re.search(pattern, self.raw_text, re.IGNORECASE)
			if match:
				return match.group(1).strip()
		
		return None
	
	def _extract_generic_utr(self) -> Optional[str]:
		"""Extract UTR/RRN if present."""
		patterns = [
			r"UTR[\.:]?\s*([A-Z0-9\-]+)",
			r"RRN[\.:]?\s*([A-Z0-9\-]+)",
		]
		
		for pattern in patterns:
			match = re.search(pattern, self.raw_text, re.IGNORECASE)
			if match:
				return match.group(1).strip()
		
		return None
	
	def _extract_generic_invoice(self) -> List[str]:
		"""Extract invoice numbers if present."""
		patterns = [
			r"Invoice\s+No[\.:]?\s*([A-Z0-9\-/]+)",
		]
		
		invoices = []
		for pattern in patterns:
			matches = re.findall(pattern, self.raw_text, re.IGNORECASE)
			invoices.extend([m.strip() for m in matches if m.strip()])
		
		return list(set(invoices)) if invoices else []
	
	def _extract_generic_amount(self) -> float:
		"""Extract amount values."""
		# Look for currency symbols followed by numbers
		patterns = [
			r"[₹$€£]\s*([\d,]+\.?\d*)",
			r"Amount[\.:]?\s*[₹$€£]?\s*([\d,]+\.?\d*)",
		]
		
		amounts = []
		for pattern in patterns:
			matches = re.findall(pattern, self.raw_text, re.IGNORECASE)
			amounts.extend([self.normalize_amount(m) for m in matches])
		
		return max(amounts) if amounts else 0.0
	
	def _extract_generic_beneficiary(self) -> Optional[str]:
		"""Extract beneficiary name if present."""
		patterns = [
			r"Beneficiary[\.:]?\s*([^\n]+)",
			r"Payee[\.:]?\s*([^\n]+)",
		]
		
		for pattern in patterns:
			match = re.search(pattern, self.raw_text, re.IGNORECASE)
			if match:
				return match.group(1).strip()
		
		return None
	
	def _extract_generic_account(self) -> Optional[str]:
		"""Extract account number if present."""
		patterns = [
			r"Account\s+No[\.:]?\s*([A-Z0-9\-]+)",
			r"A/c\s+No[\.:]?\s*([A-Z0-9\-]+)",
		]
		
		for pattern in patterns:
			match = re.search(pattern, self.raw_text, re.IGNORECASE)
			if match:
				return match.group(1).strip()
		
		return None
	
	def _extract_currency(self) -> str:
		"""Extract currency (defaults to INR)."""
		if "₹" in self.raw_text or "INR" in self.raw_text.upper():
			return "INR"
		if "USD" in self.raw_text.upper() or "$" in self.raw_text:
			return "USD"
		if "EUR" in self.raw_text.upper() or "€" in self.raw_text:
			return "EUR"
		
		return "INR"
