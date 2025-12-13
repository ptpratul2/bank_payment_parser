"""
Hindustan Zinc India Ltd Payment Advice Parser

Parses payment advice PDFs from Hindustan Zinc India Ltd.
"""

import re
from typing import Dict, Any, Optional, List
from bank_payment_parser.services.base_parser import BaseParser
import frappe


class HindustanZincParser(BaseParser):
	"""
	Parser for Hindustan Zinc India Ltd payment advice PDFs.
	
	Handles:
	- Payment Advice layout
	- Multiple date formats (DD.MM.YYYY, DD/MM/YYYY)
	- Keywords: PAYMENT ADVICE, Bank Ref No, UTR/RRN no, etc.
	- Multiple invoice rows
	"""
	
	def parse(self) -> Dict[str, Any]:
		"""
		Parse Hindustan Zinc payment advice PDF.
		
		Returns:
			Dictionary with extracted fields
		"""
		result = {
			"customer_name": self.customer_name,
			"payment_document_no": self._extract_payment_document_no(),
			"payment_date": self._extract_payment_date(),
			"bank_reference_no": self._extract_bank_reference_no(),
			"utr_rrn_no": self._extract_utr_rrn_no(),
			"invoice_no": self._extract_invoice_numbers(),
			"invoice_date": self._extract_invoice_dates(),
			"payment_amount": self._extract_payment_amount(),
			"beneficiary_name": self._extract_beneficiary_name(),
			"beneficiary_account_no": self._extract_beneficiary_account_no(),
			"bank_name": self._extract_bank_name(),
			"currency": self._extract_currency(),
			"remarks": self._extract_remarks(),
			"raw_text": self.raw_text,
			"parser_used": "HindustanZincParser",
			"parse_version": self.parse_version
		}
		
		# Validate required fields
		if not result.get("payment_document_no") and not result.get("bank_reference_no"):
			frappe.log_error(
				"Could not extract payment document number or bank reference number",
				"Hindustan Zinc Parser Validation"
			)
		
		return result
	
	def _extract_payment_document_no(self) -> Optional[str]:
		"""Extract payment document number."""
		# Try various keywords - handle both inline and multiline formats
		keywords = [
			# Pattern: "Payment Doc No : \n 2070401637" (multiline)
			r"Payment\s+Doc\s+No[\.:]?\s*:?\s*\n\s*([A-Z0-9\-]+)",
			# Pattern: "Payment Document No: 2070401637" (inline)
			r"Payment\s+Document\s+No[\.:]?\s*:?\s*([A-Z0-9\-]+)",
			# Pattern: "Payment Advice No: 2070401637"
			r"Payment\s+Advice\s+No[\.:]?\s*:?\s*([A-Z0-9\-]+)",
			# Pattern: "Advice No: 2070401637"
			r"Advice\s+No[\.:]?\s*:?\s*([A-Z0-9\-]+)",
			# Pattern: "Document No: 2070401637"
			r"Document\s+No[\.:]?\s*:?\s*([A-Z0-9\-]+)",
		]
		
		for pattern in keywords:
			match = re.search(pattern, self.raw_text, re.IGNORECASE | re.MULTILINE)
			if match:
				doc_no = match.group(1).strip()
				# Validate: Document number is typically 6-20 alphanumeric characters
				if len(doc_no) >= 6 and len(doc_no) <= 20:
					return doc_no
		
		return None
	
	def _extract_payment_date(self) -> Optional[str]:
		"""Extract payment date."""
		# Look for "Payment Date" or "Date" near payment advice
		patterns = [
			r"Payment\s+Date[\.:]?\s*(\d{1,2}[\./\-]\d{1,2}[\./\-]\d{2,4})",
			r"Date\s+of\s+Payment[\.:]?\s*(\d{1,2}[\./\-]\d{1,2}[\./\-]\d{2,4})",
			r"Date[\.:]?\s*(\d{1,2}[\./\-]\d{1,2}[\./\-]\d{2,4})",
		]
		
		for pattern in patterns:
			match = re.search(pattern, self.raw_text, re.IGNORECASE)
			if match:
				date_str = match.group(1)
				normalized = self.normalize_date(date_str)
				if normalized:
					return normalized
		
		# Try to find date near "PAYMENT ADVICE" header
		payment_advice_match = re.search(r"PAYMENT\s+ADVICE", self.raw_text, re.IGNORECASE)
		if payment_advice_match:
			# Look for date in nearby lines
			start_pos = payment_advice_match.end()
			context = self.raw_text[start_pos:start_pos + 500]
			date_match = re.search(r"(\d{1,2}[\./\-]\d{1,2}[\./\-]\d{2,4})", context)
			if date_match:
				normalized = self.normalize_date(date_match.group(1))
				if normalized:
					return normalized
		
		return None
	
	def _extract_bank_reference_no(self) -> Optional[str]:
		"""Extract bank reference number."""
		keywords = [
			r"Bank\s+Ref\s+No[\.:]?\s*([A-Z0-9\-]+)",
			r"Bank\s+Reference\s+No[\.:]?\s*([A-Z0-9\-]+)",
			r"Reference\s+No[\.:]?\s*([A-Z0-9\-]+)",
			r"Ref\s+No[\.:]?\s*([A-Z0-9\-]+)",
			# Handle "Bank Ref No : 1352908332" with colon and spaces
			r"Bank\s+Ref\s+No\s*[\.:]?\s*([A-Z0-9\-]+)",
		]
		
		for pattern in keywords:
			match = re.search(pattern, self.raw_text, re.IGNORECASE | re.MULTILINE)
			if match:
				ref_no = match.group(1).strip()
				# Validate: Bank ref is typically 6-20 alphanumeric characters
				if len(ref_no) >= 6 and len(ref_no) <= 20:
					return ref_no
		
		return None
	
	def _extract_utr_rrn_no(self) -> Optional[str]:
		"""Extract UTR/RRN number."""
		# Try most specific patterns first
		keywords = [
			# Pattern: "vide UTR/RRN no HDFCR52025120390803069" - most specific
			r"vide\s+UTR\s*/\s*RRN\s+no\s+([A-Z0-9]{10,30})",
			# Pattern: "UTR/RRN no HDFCR52025120390803069" - exact match
			r"UTR\s*/\s*RRN\s+no\s+([A-Z0-9]{10,30})",
			# Pattern: "UTR/RRN no: ABC123" with colon
			r"UTR\s*/\s*RRN\s+no[\.:]?\s+([A-Z0-9]{10,30})",
			# Pattern: "UTR No: ABC123" or "RRN No: ABC123"
			r"UTR\s+No[\.:]?\s+([A-Z0-9]{10,30})",
			r"RRN\s+No[\.:]?\s+([A-Z0-9]{10,30})",
			# Pattern: "UTR: ABC123" or "UTR/ ABC123" (without "no")
			r"UTR[/:]?\s+([A-Z0-9]{10,30})",
			r"RRN[/:]?\s+([A-Z0-9]{10,30})",
			# Pattern: UTR on separate line
			r"UTR[/:]?\s*\n\s*([A-Z0-9]{10,30})",
			r"RRN[/:]?\s*\n\s*([A-Z0-9]{10,30})",
		]
		
		for pattern in keywords:
			match = re.search(pattern, self.raw_text, re.IGNORECASE | re.MULTILINE)
			if match:
				utr = match.group(1).strip()
				# Validate: UTR/RRN is typically 10-30 alphanumeric characters
				# Exclude common false positives
				if len(utr) >= 10 and len(utr) <= 30 and utr.lower() not in ['no', 'yes', 'na', 'n/a', 'not']:
					return utr
		
		# Fallback: Look for patterns like HDFCR52025120390803069 (bank prefix + numbers)
		# This handles cases where UTR format is: BANKCODE + numbers
		bank_utr_pattern = r"\b([A-Z]{3,}[0-9]{10,})\b"
		matches = re.findall(bank_utr_pattern, self.raw_text)
		for match in matches:
			# Check if it's near UTR/RRN keywords (within 100 chars)
			match_pos = self.raw_text.find(match)
			if match_pos > 0:
				context_start = max(0, match_pos - 100)
				context_end = min(len(self.raw_text), match_pos + len(match) + 100)
				context = self.raw_text[context_start:context_end]
				if re.search(r"UTR|RRN", context, re.IGNORECASE):
					if len(match) >= 10 and len(match) <= 30:
						return match
		
		return None
	
	def _extract_invoice_numbers(self) -> List[str]:
		"""Extract invoice numbers (can be multiple)."""
		invoices = []
		
		# Look for invoice number patterns
		patterns = [
			r"Invoice\s+Number[\.:]?\s*([A-Z0-9\-/]+)",
			r"Invoice\s+No[\.:]?\s*([A-Z0-9\-/]+)",
			r"Inv\s+No[\.:]?\s*([A-Z0-9\-/]+)",
		]
		
		for pattern in patterns:
			matches = re.findall(pattern, self.raw_text, re.IGNORECASE)
			invoices.extend([m.strip() for m in matches if m.strip()])
		
		# Look for invoice table/rows
		# Pattern: Invoice numbers in a table format
		table_pattern = r"Invoice\s+Number[^\n]*\n((?:[^\n]*\n){0,10})"
		table_match = re.search(table_pattern, self.raw_text, re.IGNORECASE)
		if table_match:
			table_text = table_match.group(1)
			# Extract alphanumeric codes that look like invoice numbers
			inv_codes = re.findall(r'\b[A-Z0-9]{6,}\b', table_text)
			invoices.extend(inv_codes)
		
		# Remove duplicates and empty values
		invoices = list(set([inv for inv in invoices if inv]))
		
		return invoices if invoices else []
	
	def _extract_invoice_dates(self) -> List[str]:
		"""Extract invoice dates (can be multiple)."""
		dates = []
		
		# Look for invoice date patterns
		patterns = [
			r"Invoice\s+Date[\.:]?\s*(\d{1,2}[\./\-]\d{1,2}[\./\-]\d{2,4})",
			r"Inv\s+Date[\.:]?\s*(\d{1,2}[\./\-]\d{1,2}[\./\-]\d{2,4})",
		]
		
		for pattern in patterns:
			matches = re.findall(pattern, self.raw_text, re.IGNORECASE)
			for date_str in matches:
				normalized = self.normalize_date(date_str)
				if normalized:
					dates.append(normalized)
		
		# Remove duplicates
		dates = list(set(dates))
		
		return dates if dates else []
	
	def _extract_payment_amount(self) -> float:
		"""Extract payment amount."""
		# Look for amount patterns
		patterns = [
			r"Payment\s+Amount[\.:]?\s*[₹]?\s*([\d,]+\.?\d*)",
			r"Amount[\.:]?\s*[₹]?\s*([\d,]+\.?\d*)",
			r"Total\s+Amount[\.:]?\s*[₹]?\s*([\d,]+\.?\d*)",
			r"[₹]\s*([\d,]+\.?\d*)",
		]
		
		for pattern in patterns:
			matches = re.findall(pattern, self.raw_text, re.IGNORECASE)
			if matches:
				# Take the largest amount (likely the payment amount)
				amounts = [self.normalize_amount(m) for m in matches]
				if amounts:
					return max(amounts)
		
		return 0.0
	
	def _extract_beneficiary_name(self) -> Optional[str]:
		"""Extract beneficiary name."""
		keywords = [
			# Pattern: "Beneficiary Name : \n VAAMAN ENGINEERS INDIA LIMITED" (multiline)
			r"Beneficiary\s+Name[\.:]?\s*:?\s*\n\s*([^\n]+)",
			# Pattern: "Beneficiary Name: VAAMAN ENGINEERS INDIA LIMITED" (inline)
			r"Beneficiary\s+Name[\.:]?\s*:?\s*([^\n]+)",
			# Pattern: "Beneficiary: VAAMAN ENGINEERS INDIA LIMITED"
			r"Beneficiary[\.:]?\s*:?\s*([^\n]+)",
			# Pattern: "Payee Name: VAAMAN ENGINEERS INDIA LIMITED"
			r"Payee\s+Name[\.:]?\s*:?\s*([^\n]+)",
		]
		
		for pattern in keywords:
			match = re.search(pattern, self.raw_text, re.IGNORECASE | re.MULTILINE)
			if match:
				name = match.group(1).strip()
				# Clean up common suffixes and extra whitespace
				name = re.sub(r'[\.:]+$', '', name)
				name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
				# Exclude very short matches (likely false positives)
				if len(name) >= 3:
					return name
		
		return None
	
	def _extract_beneficiary_account_no(self) -> Optional[str]:
		"""Extract beneficiary account number."""
		keywords = [
			# Pattern: "Beneficiary Account No : \n 922030044694311" (multiline)
			r"Beneficiary\s+Account\s+No[\.:]?\s*:?\s*\n\s*([A-Z0-9\-]+)",
			# Pattern: "Beneficiary Account No: 922030044694311" (inline)
			r"Beneficiary\s+Account\s+No[\.:]?\s*:?\s*([A-Z0-9\-]+)",
			# Pattern: "Account No: 922030044694311"
			r"Account\s+No[\.:]?\s*:?\s*([A-Z0-9\-]+)",
			# Pattern: "Beneficiary A/c No: 922030044694311"
			r"Beneficiary\s+A/c\s+No[\.:]?\s*:?\s*([A-Z0-9\-]+)",
			# Pattern: "A/c No: 922030044694311"
			r"A/c\s+No[\.:]?\s*:?\s*([A-Z0-9\-]+)",
		]
		
		for pattern in keywords:
			match = re.search(pattern, self.raw_text, re.IGNORECASE | re.MULTILINE)
			if match:
				account_no = match.group(1).strip()
				# Validate: Account number is typically 9-20 alphanumeric characters
				if len(account_no) >= 9 and len(account_no) <= 20:
					return account_no
		
		return None
	
	def _extract_bank_name(self) -> Optional[str]:
		"""Extract bank name."""
		keywords = [
			r"Bank\s+Name[\.:]?\s*([^\n]+)",
			r"Beneficiary\s+Bank[\.:]?\s*([^\n]+)",
		]
		
		for pattern in keywords:
			match = re.search(pattern, self.raw_text, re.IGNORECASE)
			if match:
				bank_name = match.group(1).strip()
				# Clean up common suffixes
				bank_name = re.sub(r'[\.:]+$', '', bank_name)
				return bank_name
		
		return None
	
	def _extract_currency(self) -> str:
		"""Extract currency (defaults to INR)."""
		# Look for currency indicators
		if "₹" in self.raw_text or "INR" in self.raw_text.upper():
			return "INR"
		if "USD" in self.raw_text.upper() or "$" in self.raw_text:
			return "USD"
		if "EUR" in self.raw_text.upper() or "€" in self.raw_text:
			return "EUR"
		
		# Default to INR for Indian banks
		return "INR"
	
	def _extract_remarks(self) -> Optional[str]:
		"""Extract remarks/notes."""
		keywords = [
			r"Remarks[\.:]?\s*([^\n]+)",
			r"Notes[\.:]?\s*([^\n]+)",
			r"Description[\.:]?\s*([^\n]+)",
		]
		
		for pattern in keywords:
			match = re.search(pattern, self.raw_text, re.IGNORECASE)
			if match:
				return match.group(1).strip()
		
		return None
