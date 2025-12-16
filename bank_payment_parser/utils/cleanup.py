"""⚠️ DANGEROUS: One-time cleanup utility for Bank Payment Parser data.

⚠️⚠️⚠️ WARNING: DO NOT RUN IN PRODUCTION WITHOUT EXPLICIT CONFIRMATION ⚠️⚠️⚠️

This utility will DELETE ALL:
- Bank Payment Bulk Upload records
- Bank Payment Advice records
- Bank Payment Advice Invoice records (child table)

This is a DESTRUCTIVE operation that cannot be undone.

Usage (ONLY in development/testing):
    from bank_payment_parser.utils.cleanup import cleanup_all_data
    cleanup_all_data(confirm=True)
"""
from __future__ import annotations

import frappe
from frappe import _


def cleanup_all_data(confirm: bool = False):
	"""Delete all Bank Payment Parser data.
	
	⚠️ DESTRUCTIVE OPERATION - CANNOT BE UNDONE ⚠️
	
	This function will:
	1. Delete all Bank Payment Advice Invoice records (child table)
	2. Delete all Bank Payment Advice records
	3. Delete all Bank Payment Bulk Upload Item records (child table)
	4. Delete all Bank Payment Bulk Upload records
	
	Args:
		confirm: Must be True to proceed (safety check)
	
	Raises:
		ValueError: If confirm is not True
	"""
	if not confirm:
		raise ValueError(
			"⚠️ SAFETY CHECK FAILED: confirm must be True to proceed. "
			"This will DELETE ALL Bank Payment Parser data!"
		)
	
	# Check if we're in production (basic check)
	site_name = frappe.local.site
	if "prod" in site_name.lower() or "production" in site_name.lower():
		raise ValueError(
			"⚠️ PRODUCTION DETECTED: This utility cannot be run in production. "
			f"Site: {site_name}"
		)
	
	frappe.logger().warning(
		"⚠️ CLEANUP UTILITY STARTED: This will delete all Bank Payment Parser data!"
	)
	
	deleted_counts = {
		"Bank Payment Advice Invoice": 0,
		"Bank Payment Advice": 0,
		"Bank Payment Bulk Upload Item": 0,
		"Bank Payment Bulk Upload": 0,
	}
	
	try:
		# 1. Delete child invoice records first
		frappe.logger().info("Deleting Bank Payment Advice Invoice records...")
		invoice_names = frappe.get_all(
			"Bank Payment Advice Invoice",
			fields=["name"],
			pluck="name",
		)
		for name in invoice_names:
			frappe.db.delete("Bank Payment Advice Invoice", name)
			deleted_counts["Bank Payment Advice Invoice"] += 1
		
		# 2. Delete Bank Payment Advice records
		frappe.logger().info("Deleting Bank Payment Advice records...")
		advice_names = frappe.get_all(
			"Bank Payment Advice",
			fields=["name"],
			pluck="name",
		)
		for name in advice_names:
			frappe.db.delete("Bank Payment Advice", name)
			deleted_counts["Bank Payment Advice"] += 1
		
		# 3. Delete child bulk upload item records
		frappe.logger().info("Deleting Bank Payment Bulk Upload Item records...")
		item_names = frappe.get_all(
			"Bank Payment Bulk Upload Item",
			fields=["name"],
			pluck="name",
		)
		for name in item_names:
			frappe.db.delete("Bank Payment Bulk Upload Item", name)
			deleted_counts["Bank Payment Bulk Upload Item"] += 1
		
		# 4. Delete Bank Payment Bulk Upload records
		frappe.logger().info("Deleting Bank Payment Bulk Upload records...")
		bulk_names = frappe.get_all(
			"Bank Payment Bulk Upload",
			fields=["name"],
			pluck="name",
		)
		for name in bulk_names:
			frappe.db.delete("Bank Payment Bulk Upload", name)
			deleted_counts["Bank Payment Bulk Upload"] += 1
		
		# Commit all deletions
		frappe.db.commit()
		
		# Log summary
		total_deleted = sum(deleted_counts.values())
		frappe.logger().warning(
			f"⚠️ CLEANUP COMPLETE: Deleted {total_deleted} total records:\n"
			f"  - Bank Payment Advice Invoice: {deleted_counts['Bank Payment Advice Invoice']}\n"
			f"  - Bank Payment Advice: {deleted_counts['Bank Payment Advice']}\n"
			f"  - Bank Payment Bulk Upload Item: {deleted_counts['Bank Payment Bulk Upload Item']}\n"
			f"  - Bank Payment Bulk Upload: {deleted_counts['Bank Payment Bulk Upload']}"
		)
		
		return {
			"success": True,
			"deleted_counts": deleted_counts,
			"total_deleted": total_deleted,
		}
		
	except Exception as e:
		frappe.db.rollback()
		frappe.log_error(
			title="Cleanup Utility Error",
			message=f"Error during cleanup: {str(e)}\n\n{frappe.get_traceback()}"
		)
		raise

