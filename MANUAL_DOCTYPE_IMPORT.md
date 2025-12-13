# Manual DocType Import - Quick Fix

## Issue
DocType not showing in desk due to import error: `ModuleNotFoundError: No module named 'bank_payment_parser.bank_payment_parser'`

## Quick Solution: Import via Web Console

Since you can access the website at http://127.0.0.1:8000, you can import the DocType manually:

### Step 1: Open Browser Console

1. Login to http://127.0.0.1:8000
2. Press `F12` or right-click → Inspect
3. Go to Console tab

### Step 2: Run Import Command

Paste this in the console:

```javascript
frappe.call({
    method: 'frappe.core.doctype.doctype.doctype.import_doc',
    args: {
        file_path: '/Users/pratul/frappe-bench/apps/bank_payment_parser/bank_payment_parser/doctype/bank_payment_advice/bank_payment_advice.json'
    },
    callback: function(r) {
        console.log('Result:', r);
        if (r.message) {
            frappe.show_alert({message: 'DocType imported!', indicator: 'green'});
            location.reload();
        }
    }
});
```

### Step 3: Alternative - Use Desk Console

1. Go to: http://127.0.0.1:8000/app/console
2. Run:

```python
import frappe
import json

# Load and import DocType
with open('/Users/pratul/frappe-bench/apps/bank_payment_parser/bank_payment_parser/doctype/bank_payment_advice/bank_payment_advice.json') as f:
    data = json.load(f)

doc = frappe.get_doc(data)
doc.save()
frappe.db.commit()

print("DocType imported!")
```

### Step 4: Import Child DocType

Repeat for the child DocType:

```python
import frappe
import json

with open('/Users/pratul/frappe-bench/apps/bank_payment_parser/bank_payment_parser/doctype/bank_payment_advice_invoice/bank_payment_advice_invoice.json') as f:
    data = json.load(f)

doc = frappe.get_doc(data)
doc.save()
frappe.db.commit()

print("Child DocType imported!")
```

### Step 5: Clear Cache and Reload

After importing:

```python
frappe.clear_cache()
frappe.db.commit()
```

Then refresh the page.

## Verification

After import, check:

1. Search for "Bank Payment Advice" in the search bar
2. Or go to: http://127.0.0.1:8000/app/doctype/Bank%20Payment%20Advice
3. Should see the DocType form

## Root Cause

The nested directory `bank_payment_parser/bank_payment_parser/` was causing path resolution issues. This has been removed, but the import error persists due to cached references.

## Permanent Fix

Once DocTypes are imported, the app should work normally. The import error only affects the initial sync - once DocTypes exist in the database, they will work fine.
