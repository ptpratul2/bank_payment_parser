# Bank Payment Parser

A scalable, production-ready Frappe app for parsing customer-specific bank payment advice PDFs. Built with extensibility in mind, allowing easy addition of new customer formats without modifying existing code.

## Features

- ✅ **Customer-Specific Parsing**: Each customer has its own dedicated parser
- ✅ **Strategy Pattern Architecture**: Clean, extensible design
- ✅ **Auto-Detection**: Automatically detects customer from PDF content
- ✅ **Manual Selection**: Users can manually select customer during upload
- ✅ **OCR Support**: Optional OCR for scanned PDFs
- ✅ **Background Processing**: Non-blocking PDF parsing
- ✅ **Bulk Upload**: Upload and process multiple PDFs at once
- ✅ **Queue-Based Processing**: Each PDF processed in separate background job
- ✅ **Duplicate Prevention**: Prevents duplicate payment advice records
- ✅ **Production Ready**: Error handling, logging, and validation

## Installation

### Prerequisites

- Frappe/ERPNext v15
- Python 3.8+
- Required Python packages (installed automatically):
  - `pdfminer.six` - PDF text extraction
  - `pytesseract` (optional) - OCR support
  - `pdf2image` (optional) - OCR support
  - `Pillow` (optional) - OCR support

### Install the App

```bash
# Get the app
cd /path/to/frappe-bench
bench get-app bank_payment_parser

# Install on site
bench --site your-site.local install-app bank_payment_parser
```

### Install OCR Dependencies (Optional)

If you need OCR support for scanned PDFs:

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install tesseract-ocr poppler-utils

# Install Python packages
pip install pytesseract pdf2image Pillow
```

## Usage

### Basic Workflow

1. **Create Bank Payment Advice**: Navigate to Bank Payment Advice list
2. **Upload PDF**: Attach the payment advice PDF file
3. **Select Customer**: Choose the customer from the dropdown (or let it auto-detect)
4. **Parse PDF**: Click "Parse PDF" button
5. **Review & Submit**: Review extracted data and submit

### API Usage

#### Parse PDF (Synchronous)

```python
import frappe

result = frappe.call(
    "bank_payment_parser.api.upload.upload_and_parse",
    file_url="/files/payment_advice.pdf",
    customer="Hindustan Zinc India Ltd",
    use_ocr=False
)

print(result["parsed_data"])
```

#### Create Payment Advice (Synchronous)

```python
result = frappe.call(
    "bank_payment_parser.api.upload.create_payment_advice",
    file_url="/files/payment_advice.pdf",
    customer="Hindustan Zinc India Ltd"
)

print(f"Created: {result['name']}")
```

#### Parse in Background (Asynchronous)

```python
result = frappe.call(
    "bank_payment_parser.api.upload.parse_in_background",
    file_url="/files/payment_advice.pdf",
    customer="Hindustan Zinc India Ltd"
)

print(f"Job ID: {result['job_id']}")
```

### Bulk Upload Workflow

The app supports bulk upload and processing of multiple PDFs at once.

#### Using Desk UI

1. **Navigate to Bulk Upload**: Go to Bank Payment Bulk Upload list
2. **Create New**: Click "New" to create a bulk upload record
3. **Select Customer**: Choose the customer (required)
4. **Upload PDFs**: Click "Upload PDFs" button
   - Drag and drop multiple PDF files OR
   - Click "Select Files" to browse
5. **Submit**: Submit the document to start background processing
6. **Monitor Progress**: Watch the status indicators:
   - **Queued**: Files uploaded, waiting to process
   - **Processing**: Files being processed in background
   - **Completed**: All files processed successfully
   - **Partial**: Some files succeeded, some failed
   - **Failed**: All files failed
7. **Reprocess Failed**: Click "Reprocess Failed" button to retry failed files

#### API Usage

```python
# Create bulk upload
result = frappe.call(
    "bank_payment_parser.api.bulk_upload.create_bulk_upload",
    customer="Hindustan Zinc India Ltd",
    files=[
        {"name": "file1.pdf", "size": 1024, "type": "application/pdf"},
        {"name": "file2.pdf", "size": 2048, "type": "application/pdf"}
    ]
)

bulk_upload_name = result["bulk_upload_name"]

# Add files (after uploading via file API)
frappe.call(
    "bank_payment_parser.api.bulk_upload.add_file_to_bulk_upload",
    bulk_upload_name=bulk_upload_name,
    file_url="/files/file1.pdf",
    file_name="file1.pdf"
)

# Submit the bulk upload document to start processing
bulk_upload = frappe.get_doc("Bank Payment Bulk Upload", bulk_upload_name)
bulk_upload.submit()

# Check status
status = frappe.call(
    "bank_payment_parser.api.bulk_upload.get_bulk_upload_status",
    bulk_upload_name=bulk_upload_name
)

print(f"Status: {status['status']}")
print(f"Processed: {status['processed_files']}/{status['total_files']}")
print(f"Success: {status['success_count']}, Failed: {status['failed_count']}")

# Reprocess failed files
frappe.call(
    "bank_payment_parser.api.bulk_upload.reprocess_failed",
    bulk_upload_name=bulk_upload_name
)
```

#### Bulk Processing Architecture

- **Queue-Based**: Each PDF is processed in a separate background job
- **Non-Blocking**: One failure doesn't stop other files from processing
- **Status Tracking**: Real-time status updates for each file
- **Re-Processing**: Easy retry mechanism for failed files
- **Performance**: Handles 100+ PDFs safely with proper queue management

#### Performance Notes

- Each PDF is processed in a separate background job (queue: `long`)
- Jobs have a 5-minute timeout per file
- Processing happens asynchronously - UI remains responsive
- Status auto-refreshes every 5 seconds during processing
- Failed files can be reprocessed without affecting successful ones

## Architecture

### Parser Structure

```
bank_payment_parser/
├── services/
│   ├── base_parser.py          # Abstract base class
│   ├── parser_factory.py      # Customer detection & parser selection
│   ├── hindustan_zinc.py      # Hindustan Zinc parser
│   ├── generic_parser.py       # Fallback parser
│   └── ocr_utils.py           # OCR utilities
├── api/
│   ├── upload.py              # Single file upload & parsing endpoints
│   └── bulk_upload.py         # Bulk upload endpoints
├── jobs/
│   └── bulk_processor.py      # Background job handlers for bulk processing
└── doctype/
    ├── bank_payment_advice/    # Main doctype
    ├── bank_payment_bulk_upload/        # Bulk upload tracking
    └── bank_payment_bulk_upload_item/    # Individual file tracking
```

### Strategy Pattern

The app uses the **Strategy Pattern** for parsing:

1. **BaseParser**: Abstract base class defining the interface
2. **Customer Parsers**: Specific implementations (e.g., `HindustanZincParser`)
3. **ParserFactory**: Detects customer and returns appropriate parser
4. **GenericParser**: Fallback for unsupported formats

## Extending the App: Adding a New Customer Parser

### Step 1: Create Parser Class

Create a new file: `bank_payment_parser/services/your_customer.py`

```python
from bank_payment_parser.services.base_parser import BaseParser
from typing import Dict, Any, Optional
import re
import frappe


class YourCustomerParser(BaseParser):
    """
    Parser for Your Customer payment advice PDFs.
    """
    
    def parse(self) -> Dict[str, Any]:
        """
        Parse payment advice PDF.
        
        Returns:
            Dictionary with standardized fields
        """
        result = {
            "customer_name": self.customer_name,
            "payment_document_no": self._extract_document_no(),
            "payment_date": self._extract_payment_date(),
            "bank_reference_no": self._extract_bank_ref(),
            "utr_rrn_no": self._extract_utr(),
            "invoice_no": self._extract_invoices(),
            "invoice_date": self._extract_invoice_dates(),
            "payment_amount": self._extract_amount(),
            "beneficiary_name": self._extract_beneficiary(),
            "beneficiary_account_no": self._extract_account(),
            "bank_name": self._extract_bank(),
            "currency": self._extract_currency(),
            "remarks": self._extract_remarks(),
            "raw_text": self.raw_text,
            "parser_used": "YourCustomerParser",
            "parse_version": self.parse_version
        }
        
        return result
    
    def _extract_document_no(self) -> Optional[str]:
        """Extract payment document number."""
        # Use regex patterns specific to your customer's format
        pattern = r"Document\s+No[\.:]?\s*([A-Z0-9\-]+)"
        match = re.search(pattern, self.raw_text, re.IGNORECASE)
        return match.group(1).strip() if match else None
    
    def _extract_payment_date(self) -> Optional[str]:
        """Extract payment date."""
        pattern = r"Date[\.:]?\s*(\d{1,2}[\./\-]\d{1,2}[\./\-]\d{2,4})"
        match = re.search(pattern, self.raw_text, re.IGNORECASE)
        if match:
            return self.normalize_date(match.group(1))
        return None
    
    # Implement other extraction methods...
    # Use helper methods from BaseParser:
    # - self.normalize_date()
    # - self.normalize_amount()
    # - self.extract_by_keyword()
    # - self.extract_multiple_by_keyword()
```

### Step 2: Register Parser

Edit `bank_payment_parser/services/parser_factory.py`:

```python
from bank_payment_parser.services.your_customer import YourCustomerParser

# Add to PARSER_REGISTRY
PARSER_REGISTRY = {
    "Hindustan Zinc India Ltd": HindustanZincParser,
    "Your Customer Ltd": YourCustomerParser,  # Add this line
    # ...
}

# Optionally add keyword detection
def detect_customer_from_text(text: str) -> Optional[str]:
    # ... existing code ...
    
    # Add your customer keywords
    customer_keywords = {
        "HINDUSTAN ZINC": "Hindustan Zinc India Ltd",
        "YOUR CUSTOMER": "Your Customer Ltd",  # Add this
        # ...
    }
```

### Step 3: Test Your Parser

```python
# In Frappe console
from bank_payment_parser.services.your_customer import YourCustomerParser
from bank_payment_parser.services.ocr_utils import extract_text_from_pdf

pdf_path = "/path/to/test.pdf"
text = extract_text_from_pdf(pdf_path)
parser = YourCustomerParser(pdf_path, text, "Your Customer Ltd")
result = parser.parse()
print(result)
```

### Step 4: Deploy

1. Restart Frappe bench
2. Test with a real PDF
3. Monitor logs for any errors

## Supported Customers

Currently supported customers:

- ✅ **Hindustan Zinc India Ltd** - Full parser implementation
- ⚠️ **Generic Parser** - Fallback for unsupported formats

## Field Mapping

### Standardized Output Fields

All parsers must return these fields:

| Field | Type | Description |
|-------|------|-------------|
| `customer_name` | str | Customer/paying company name |
| `payment_document_no` | str | Payment document number |
| `payment_date` | str | Payment date (YYYY-MM-DD) |
| `bank_reference_no` | str | Bank reference number |
| `utr_rrn_no` | str | UTR/RRN number |
| `invoice_no` | str/list | Invoice number(s) |
| `invoice_date` | str/list | Invoice date(s) |
| `payment_amount` | float | Payment amount |
| `beneficiary_name` | str | Beneficiary name |
| `beneficiary_account_no` | str | Beneficiary account number |
| `bank_name` | str | Bank name |
| `currency` | str | Currency code (default: INR) |
| `remarks` | str | Remarks/notes |
| `raw_text` | str | Extracted raw text |
| `parser_used` | str | Parser class name |
| `parse_version` | str | Parser version |

## Error Handling

### Parse Status

- **Draft**: Document created, not yet parsed
- **Parsed**: Successfully parsed
- **Error**: Parsing failed (check `parsing_error` field)

### Common Issues

1. **PDF text extraction fails**
   - Enable OCR: Set `use_ocr=True` in API call
   - Ensure PDF is not corrupted

2. **Customer not detected**
   - Manually select customer during upload
   - Check if customer name matches registry exactly

3. **Duplicate UTR/RRN**
   - System prevents duplicates automatically
   - Check existing records before creating new ones

## Reporting

### Customer-wise Reports

Create custom reports using Frappe's Report Builder:

- Filter by `customer`
- Group by `payment_date`
- Sum `payment_amount`

### Bank-wise Summary

- Filter by `bank_name`
- Group by month
- Calculate totals

## Development

### Running Tests

```bash
# Run doctype tests
bench --site your-site.local run-tests --doctype "Bank Payment Advice"

# Run app tests
bench --site your-site.local run-tests --app bank_payment_parser
```

### Debugging

Enable verbose logging:

```python
import frappe
frappe.conf.developer_mode = 1
```

Check logs:
```bash
tail -f logs/web.log
```

## Best Practices

1. **Parser Development**
   - Use regex patterns, not fixed line numbers
   - Handle multiple date formats
   - Test with various PDF layouts
   - Log extraction failures

2. **Error Handling**
   - Always return a valid dictionary
   - Use `None` for missing optional fields
   - Provide meaningful error messages

3. **Performance**
   - Use background jobs for large files
   - Cache parsed results if needed
   - Optimize regex patterns

## License

MIT License

## Support

For issues, questions, or contributions, please contact the development team.

---

**Version**: 1.0.0  
**Compatible with**: Frappe/ERPNext v15  
**Last Updated**: January 2025
