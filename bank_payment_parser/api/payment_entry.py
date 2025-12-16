"""API endpoints for Payment Entry creation from Bank Payment Advice."""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import today


@frappe.whitelist()
def create_payment_entry(advice_name: str):
	"""Create a Payment Entry (Receive) from Bank Payment Advice.
	
	Args:
		advice_name: Name of the Bank Payment Advice document
	
	Returns:
		Dictionary with payment_entry name and redirect URL
	"""
	# Validate advice document
	advice = frappe.get_doc("Bank Payment Advice", advice_name)
	
	# Check prerequisites
	if advice.docstatus != 1:
		frappe.throw(_("Bank Payment Advice must be submitted before creating Payment Entry"))
	
	if advice.parse_status != "Parsed":
		frappe.throw(_("Bank Payment Advice must be parsed before creating Payment Entry"))
	
	if advice.payment_entry:
		frappe.throw(_("Payment Entry already created: {0}").format(advice.payment_entry))
	
	if not advice.total_received_amount or advice.total_received_amount <= 0:
		frappe.throw(_("Total Received Amount must be greater than zero"))
	
	if not advice.customer:
		frappe.throw(_("Customer is required to create Payment Entry"))
	
	# Get customer account
	from erpnext.accounts.utils import get_account_currency
	from erpnext.accounts.party import get_party_account
	from erpnext import get_company_currency
	
	company = frappe.defaults.get_user_default("Company")
	if not company:
		frappe.throw(_("Please set default Company in User Preferences"))
	
	# Get party account (Customer) using ERPNext utility function
	party_account = get_party_account("Customer", advice.customer, company)
	
	if not party_account:
		frappe.throw(
			_("Party Account not found for Customer {0} in Company {1}").format(
				advice.customer, company
			)
		)
	
	# Get default bank account for the company (optional)
	# User can change this in Payment Entry form if needed
	bank_account = frappe.db.get_value(
		"Account",
		{"account_type": "Bank", "company": company, "is_group": 0},
		"name",
		order_by="creation desc",
	)
	
	# Create Payment Entry
	payment_entry = frappe.get_doc({
		"doctype": "Payment Entry",
		"payment_type": "Receive",
		"party_type": "Customer",
		"party": advice.customer,
		"posting_date": advice.payment_date or today(),
		"paid_amount": advice.total_received_amount,
		"received_amount": advice.total_received_amount,
		"paid_to": party_account,
		"paid_to_account_currency": get_account_currency(party_account),
		"source_exchange_rate": 1.0,
		"target_exchange_rate": 1.0,
		"reference_no": advice.utr_rrn_no or advice.bank_reference_no,
		"reference_date": advice.payment_date or today(),
		"company": company,
		"currency": advice.currency or get_company_currency(company),
		"remarks": _("Created from Bank Payment Advice {0}").format(advice.name),
	})
	
	# Set bank account if available (paid_from for Receive type)
	if bank_account:
		payment_entry.paid_from = bank_account
		payment_entry.paid_from_account_currency = get_account_currency(bank_account)
	
	# Save Payment Entry
	payment_entry.insert(ignore_permissions=True)
	frappe.db.commit()
	
	# Link back to Bank Payment Advice (use direct DB update to bypass submit restrictions)
	frappe.db.set_value(
		"Bank Payment Advice",
		advice_name,
		"payment_entry",
		payment_entry.name,
		update_modified=False,
	)
	frappe.db.commit()
	
	return {
		"success": True,
		"payment_entry": payment_entry.name,
		"message": _("Payment Entry {0} created successfully").format(payment_entry.name),
	}

