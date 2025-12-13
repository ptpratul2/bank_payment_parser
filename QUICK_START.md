# Quick Start Guide

## Installation

```bash
# 1. Get the app
cd /path/to/frappe-bench
bench get-app bank_payment_parser

# 2. Install on your site
bench --site your-site.local install-app bank_payment_parser

# 3. Migrate (if needed)
bench --site your-site.local migrate
```

## First Use

1. **Navigate to Bank Payment Advice**
   - Go to: Bank Payment Parser > Bank Payment Advice

2. **Create New Document**
   - Click "New"
   - Select Customer (e.g., "Hindustan Zinc India Ltd")
   - Upload PDF file
   - Click "Parse PDF" button

3. **Review & Submit**
   - Review extracted data
   - Make corrections if needed
   - Submit document

## Testing with Sample PDFs

The app includes sample PDFs for testing:
- `CR1352915104_1352915104.pdf` - Hindustan Zinc format
- `CR1352908332_HDFCR52025120390803069.pdf` - HDFC format

## API Quick Test

```python
# In Frappe console (bench console)
import frappe

# Parse a PDF
result = frappe.call(
    "bank_payment_parser.api.upload.upload_and_parse",
    file_url="/files/your_pdf.pdf",
    customer="Hindustan Zinc India Ltd"
)

print(result)
```

## Troubleshooting

### PDF Not Parsing

1. Check if PDF contains text (not just images)
2. Enable OCR: Set `use_ocr=True` in API call
3. Check logs: `tail -f logs/web.log`

### Customer Not Detected

1. Manually select customer from dropdown
2. Check if customer name matches exactly in parser registry
3. Review raw_text field to see extracted content

### Duplicate Error

- System prevents duplicate UTR/RRN
- Check existing records before creating new ones

## Next Steps

- Read [README.md](README.md) for detailed documentation
- See "Extending the App" section to add new customer parsers
- Customize reports as needed
