# How to Use Bank Payment Parser

## 📤 Upload and Parse PDF - Step by Step

### Step 1: Navigate to Bank Payment Advice

1. **Login** to your Frappe site: http://127.0.0.1:8000
2. **Search** for "Bank Payment Advice" in the search bar (top right)
3. **Or navigate**: Bank Payment Parser > Bank Payment Advice

### Step 2: Create New Document

1. Click **"New"** button (top right)
2. A new Bank Payment Advice form will open

### Step 3: Select Customer

1. In the **"Customer"** field (first field), select the customer
   - Example: "Hindustan Zinc India Ltd"
   - Or select from the dropdown
2. This helps the system choose the correct parser

### Step 4: Upload PDF

1. Scroll down to **"Parsing Information"** section
2. Find the **"PDF File"** field
3. Click the **"Attach"** button or drag & drop your PDF file
4. Select your payment advice PDF (e.g., `CR1352915104_1352915104.pdf`)
5. Wait for upload to complete

### Step 5: Parse PDF

1. After PDF is uploaded, a **"Parse PDF"** button will appear at the top
2. Click **"Parse PDF"** button
3. Wait for parsing to complete (shows "Parsing PDF..." message)

### Step 6: Review Extracted Data

After parsing:
- ✅ All fields will be automatically filled
- ✅ Invoice details will be added to the table
- ✅ Parse status will change to "Parsed"
- ✅ Parser used will be displayed

### Step 7: Save and Submit

1. **Review** all extracted data
2. **Make corrections** if needed
3. Click **"Save"** to save the document
4. Click **"Submit"** to finalize (document becomes read-only after submit)

## 🎯 Quick Access URLs

- **List View**: http://127.0.0.1:8000/app/bank-payment-advice
- **New Document**: http://127.0.0.1:8000/app/bank-payment-advice/new
- **Search**: Use search bar in Frappe Desk

## 📋 Field Locations

The form has these sections:

1. **Payment Details**
   - Customer (required)
   - Payment Document No
   - Payment Date
   - Bank Reference No
   - UTR/RRN No
   - Payment Amount
   - Currency

2. **Parsing Information**
   - PDF File ← **Upload here!**
   - Parser Used (auto-filled)
   - Parse Status
   - Parsing Error (if any)

3. **Beneficiary Details**
   - Beneficiary Name
   - Beneficiary Account No
   - Bank Name
   - Remarks

4. **Invoice Details** (table)
   - Invoice Number
   - Invoice Date
   - Amount

5. **Raw Data**
   - Raw Text (extracted PDF text)

## 🔍 Tips

- **Customer Selection**: If you don't select a customer, the system will try to auto-detect from PDF
- **Multiple Invoices**: If the PDF has multiple invoices, they'll all be added to the table
- **Parse Button**: Only appears after PDF is uploaded
- **Error Handling**: If parsing fails, check the "Parsing Error" field for details

## 🚀 Example Workflow

```
1. New → Bank Payment Advice
2. Customer: "Hindustan Zinc India Ltd"
3. Upload: CR1352915104_1352915104.pdf
4. Click: "Parse PDF"
5. Review: All fields auto-filled
6. Save → Submit
```

## ❓ Troubleshooting

### Parse Button Not Appearing
- Make sure PDF is fully uploaded
- Check if PDF file field has a value
- Refresh the page if needed

### Parsing Fails
- Check "Parsing Error" field for details
- Verify PDF contains text (not just images)
- Try selecting customer manually
- Check if customer parser is registered

### Fields Not Filled
- Some fields may be empty if not found in PDF
- Check "Raw Text" field to see what was extracted
- Manually fill missing fields if needed

---

**Ready to use!** The DocType is now working. Just create a new document and upload your PDF.
