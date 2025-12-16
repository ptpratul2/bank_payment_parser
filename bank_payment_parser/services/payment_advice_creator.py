"""Centralized service for creating Bank Payment Advice documents.

This service centralizes the logic for creating Bank Payment Advice
documents from parsed data, ensuring consistency between bulk and
single-file processing.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import frappe
from frappe import _


def create_payment_advice_from_parsed_data(
	parsed_data: Dict[str, Any],
	file_url: str,
	file_type: str,
	customer: Optional[str] = None,
	bulk_upload_reference: Optional[str] = None,
) -> frappe.Document:
	"""Create a Bank Payment Advice document from parsed data.
	
	This is the single source of truth for creating payment advice
	documents, used by both bulk and single-file processing.
	
	Args:
		parsed_data: Dictionary of parsed payment data from parser
		file_url: URL of the source file (PDF or XML)
		file_type: "PDF" or "XML"
		customer: Optional customer name (overrides parsed customer)
		bulk_upload_reference: Optional bulk upload reference
	
	Returns:
		Bank Payment Advice document (not yet saved)
	"""
	# Create Bank Payment Advice document with accounting fields
	payment_advice = frappe.get_doc({
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
		"raw_payload": parsed_data.get("raw_xml") or parsed_data.get("raw_text"),
		"parser_used": parsed_data.get("parser_used"),
		"parse_version": parsed_data.get("parse_version"),
		"parse_status": "Parsed",
		"file_type": file_type,
		"parser_type": parsed_data.get("parser_type"),
		"source_format": parsed_data.get("source_format"),
		"bulk_upload_reference": bulk_upload_reference,
		# Accounting fields
		"gross_payment_amount": parsed_data.get("gross_payment_amount", 0),
		"payment_method": parsed_data.get("payment_method"),
		"payer_name": parsed_data.get("payer_name"),
		"payer_city": parsed_data.get("payer_city"),
	})
	
	# Add invoice details
	_add_invoice_rows(payment_advice, parsed_data)
	
	# Trigger validation to calculate accounting fields
	payment_advice.validate()
	
	return payment_advice


def _add_invoice_rows(payment_advice: frappe.Document, parsed_data: Dict[str, Any]) -> None:
	"""Add invoice rows to payment advice from parsed data.
	
	Supports both structured invoice_table_data and legacy formats.
	"""
	invoice_table_data = parsed_data.get("invoice_table_data", [])
	total_amount = parsed_data.get("payment_amount", 0) or 0
	
	if invoice_table_data:
		# Use structured invoice table data
		per_invoice = total_amount / len(invoice_table_data) if len(invoice_table_data) else 0
		
		for row in invoice_table_data:
			invoice_number = row.get("invoice_number_pf") or row.get("invoice_number")
			if not invoice_number:
				continue
			
			invoice_date = row.get("invoice_date_advanced_adjusted") or row.get("invoice_date")
			tds_wct = row.get("tds_wct") or row.get("tds_amount") or row.get("invoice_tds_amount", 0.0)
			other_ded = row.get("other_deductions_security_retention", 0.0)
			amount = row.get("invoice_amount") or row.get("invoice_net_amount", per_invoice)
			
			# Extract invoice-level accounting fields
			invoice_gross = row.get("invoice_gross_amount") or row.get("gross_amount")
			invoice_net = row.get("invoice_net_amount") or row.get("invoice_amount")
			invoice_tds = row.get("invoice_tds_amount") or row.get("tds_amount", 0.0)
			invoice_adj = row.get("invoice_adjustment_amount", 0.0)
			
			payment_advice.append("invoices", {
				"invoice_number_pf": invoice_number,
				"invoice_date_advanced_adjusted": invoice_date,
				"invoice_gross_amount": invoice_gross,
				"invoice_net_amount": invoice_net,
				"invoice_tds_amount": invoice_tds,
				"invoice_adjustment_amount": invoice_adj,
				"tds_wct": tds_wct,  # Backward compatibility
				"other_deductions_security_retention": other_ded,
				"amount": amount,
			})
	else:
		# Fallback to legacy format (simple lists)
		invoice_nos = parsed_data.get("invoice_no", [])
		invoice_dates = parsed_data.get("invoice_date", [])
		
		# Normalize to lists
		if invoice_nos and isinstance(invoice_nos, str):
			invoice_nos = [invoice_nos]
		if invoice_dates and isinstance(invoice_dates, str):
			invoice_dates = [invoice_dates]
		
		if invoice_nos:
			amount_per_invoice = total_amount / len(invoice_nos) if len(invoice_nos) else 0
			
			for idx, invoice_no in enumerate(invoice_nos):
				if invoice_no:
					payment_advice.append("invoices", {
						"invoice_number_pf": invoice_no,
						"invoice_date_advanced_adjusted": invoice_dates[idx] if idx < len(invoice_dates) and invoice_dates[idx] else None,
						"amount": amount_per_invoice,
					})

