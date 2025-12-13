# Bulk PDF Upload & Processing Guide

## Overview

The bulk upload feature allows you to upload and process multiple bank payment advice PDFs simultaneously. Each PDF is processed in a separate background job, ensuring that one failure doesn't block others.

## Features

✅ **Multi-File Upload**: Upload 10, 50, or 100+ PDFs at once  
✅ **Queue-Based Processing**: Each PDF processed in separate background job  
✅ **Real-Time Status**: Track progress for each file individually  
✅ **Error Isolation**: Failed files don't stop successful ones  
✅ **Reprocess Failed**: One-click retry for failed files  
✅ **Customer-Wise Routing**: Automatically uses correct parser per customer  
✅ **Production-Safe**: Handles large batches without memory issues  

## Usage

### Step 1: Create Bulk Upload Record

1. Navigate to **Bank Payment Bulk Upload** list
2. Click **New**
3. Select **Customer** (required)
4. Click **Save**

### Step 2: Upload PDFs

1. Click **Upload PDFs** button
2. In the dialog:
   - **Drag and drop** multiple PDF files, OR
   - Click **Select Files** to browse
3. Review the file list
4. Click **Upload & Process**

### Step 3: Submit to Start Processing

1. Review the uploaded files in the child table
2. Click **Submit** to start background processing
3. Status will change to **Processing**

### Step 4: Monitor Progress

The form shows:
- **Total Files**: Number of files uploaded
- **Processed Files**: Number completed (success + failed)
- **Success Count**: Number successfully parsed
- **Failed Count**: Number that failed
- **Status**: Overall status (Queued/Processing/Completed/Partial/Failed)

Each child row shows:
- **File Name**: Original filename
- **Parse Status**: Pending/Success/Failed
- **Parsed Document**: Link to created Bank Payment Advice (if successful)
- **Error Message**: Error details (if failed)
- **Parser Used**: Which parser was used

### Step 5: Reprocess Failed Files

If some files failed:
1. Click **Reprocess Failed** button
2. Failed files will be reset and re-queued
3. Processing will restart automatically

## Status Meanings

| Status | Meaning |
|--------|---------|
| **Queued** | Files uploaded, waiting to process |
| **Processing** | Files being processed in background |
| **Completed** | All files processed successfully |
| **Partial** | Some succeeded, some failed |
| **Failed** | All files failed |

## Architecture

### Background Processing

- Each PDF is processed in a **separate background job**
- Jobs run in `long` queue (5-minute timeout per file)
- Processing is **non-blocking** - UI remains responsive
- Status auto-updates every 5 seconds during processing

### Parser Reuse

The bulk upload system **reuses all existing parsing logic**:
- Uses `ParserFactory` for customer detection
- Routes to customer-specific parsers (e.g., Hindustan Zinc)
- Falls back to GenericParser if needed
- No duplicate code - same parsers as single-file upload

### Error Handling

- Each file's error is captured separately
- Errors logged to Frappe Error Log
- Error messages stored in child row
- Failed files can be reprocessed without affecting others

## Performance

### Recommended Batch Sizes

- **Small**: 10-20 files (fast processing)
- **Medium**: 50-100 files (good for regular use)
- **Large**: 100+ files (may take longer, but safe)

### Processing Time

- **Per File**: 10-60 seconds (depending on PDF complexity)
- **Batch of 50**: ~10-30 minutes
- **Batch of 100**: ~20-60 minutes

### Best Practices

1. **Upload in batches**: Don't upload 500+ files at once
2. **Monitor progress**: Check status periodically
3. **Reprocess failed**: Don't delete failed files, reprocess them
4. **Check logs**: Review error logs for patterns

## API Usage

### Create Bulk Upload

```python
result = frappe.call(
    "bank_payment_parser.api.bulk_upload.create_bulk_upload",
    customer="Hindustan Zinc India Ltd",
    files=[{"name": "file1.pdf", "size": 1024, "type": "application/pdf"}]
)
```

### Add File to Bulk Upload

```python
frappe.call(
    "bank_payment_parser.api.bulk_upload.add_file_to_bulk_upload",
    bulk_upload_name="BPBU-2025-00001",
    file_url="/files/file1.pdf",
    file_name="file1.pdf"
)
```

### Check Status

```python
status = frappe.call(
    "bank_payment_parser.api.bulk_upload.get_bulk_upload_status",
    bulk_upload_name="BPBU-2025-00001"
)
```

### Reprocess Failed

```python
frappe.call(
    "bank_payment_parser.api.bulk_upload.reprocess_failed",
    bulk_upload_name="BPBU-2025-00001"
)
```

## Troubleshooting

### Files Not Processing

1. **Check Background Jobs**: Go to System > Background Jobs
2. **Check Queue**: Ensure `long` queue is running
3. **Check Logs**: Review error logs for details

### All Files Failing

1. **Check Customer**: Ensure customer is selected correctly
2. **Check PDF Format**: Verify PDFs are valid and contain text
3. **Check Parser**: Ensure customer has a registered parser

### Slow Processing

1. **Normal**: Large batches take time
2. **Check Queue**: Ensure background workers are running
3. **Reduce Batch Size**: Try smaller batches

## Future Enhancements (Not Enabled)

The following features are planned but not yet implemented:

- ⏳ **ML Fallback Parsing**: Automatic format detection using ML
- ⏳ **Confidence Score**: Parser confidence rating per field
- ⏳ **Manual Review Workflow**: Flag low-confidence extractions

These will be added in future releases.
