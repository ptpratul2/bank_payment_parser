# Installation Guide

## Prerequisites

1. Frappe/ERPNext v15 installed and running
2. Python 3.10+ 
3. Access to your site database

## Installation Steps

### Step 1: Verify App Structure

The app should be located at:
```
/Users/pratul/frappe-bench/apps/bank_payment_parser/
```

Verify the structure:
```bash
cd /Users/pratul/frappe-bench/apps/bank_payment_parser
ls -la bank_payment_parser/
```

You should see:
- `hooks.py`
- `modules.txt`
- `api/`, `services/`, `doctype/`, `utils/`, `public/` directories

### Step 2: Add App to Bench (if not already added)

Since the app is already in `apps/` directory, you can either:

**Option A: Install directly (if app is already in apps/)**
```bash
cd /Users/pratul/frappe-bench
bench --site <your-site-name> install-app bank_payment_parser
```

**Option B: Add to apps.txt first**
```bash
# Add to sites/apps.txt
echo "bank_payment_parser" >> sites/apps.txt

# Then install
bench --site <your-site-name> install-app bank_payment_parser
```

### Step 3: Install Dependencies

Install required Python packages:
```bash
cd /Users/pratul/frappe-bench
bench pip install pdfminer.six
```

For OCR support (optional):
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install tesseract-ocr poppler-utils

# Install Python packages
bench pip install pytesseract pdf2image Pillow
```

### Step 4: Install App on Site

```bash
# Replace <your-site-name> with your actual site name
bench --site <your-site-name> install-app bank_payment_parser
```

### Step 5: Migrate Database

```bash
bench --site <your-site-name> migrate
```

### Step 6: Restart Bench

```bash
bench restart
```

## Troubleshooting

### Issue: "Access denied for user" (Database Error)

This is a database connection issue, not an app issue. Solutions:

1. **Check site configuration:**
   ```bash
   cat sites/<your-site-name>/site_config.json
   ```

2. **Verify database credentials:**
   - Check if database user exists
   - Verify password is correct
   - Ensure database server is running

3. **Try connecting to database manually:**
   ```bash
   mysql -u <db_user> -p <db_name>
   ```

### Issue: "App not found"

1. **Verify app is in correct location:**
   ```bash
   ls -la apps/bank_payment_parser/bank_payment_parser/hooks.py
   ```

2. **Check if app is in apps.txt:**
   ```bash
   cat sites/apps.txt | grep bank_payment_parser
   ```

3. **Add app manually:**
   ```bash
   echo "bank_payment_parser" >> sites/apps.txt
   ```

### Issue: "Module not found" or Import Errors

1. **Check Python syntax:**
   ```bash
   cd apps/bank_payment_parser
   python3 -m py_compile bank_payment_parser/**/*.py
   ```

2. **Verify all __init__.py files exist:**
   ```bash
   find bank_payment_parser -name "__init__.py"
   ```

3. **Clear Python cache:**
   ```bash
   find . -type d -name __pycache__ -exec rm -r {} +
   find . -name "*.pyc" -delete
   ```

### Issue: "DocType not found" after installation

1. **Clear cache:**
   ```bash
   bench --site <your-site-name> clear-cache
   ```

2. **Rebuild assets:**
   ```bash
   bench --site <your-site-name> build
   ```

3. **Restart bench:**
   ```bash
   bench restart
   ```

## Verification

After installation, verify:

1. **Check app is installed:**
   ```bash
   bench --site <your-site-name> list-apps | grep bank_payment_parser
   ```

2. **Check DocType exists:**
   - Login to Frappe
   - Go to: Bank Payment Parser > Bank Payment Advice
   - Should see the list view

3. **Test parsing:**
   - Create new Bank Payment Advice
   - Upload a PDF
   - Click "Parse PDF" button

## Alternative: Manual Installation

If `bench install-app` fails, you can manually install:

1. **Add to apps.txt:**
   ```bash
   echo "bank_payment_parser" >> sites/apps.txt
   ```

2. **Install Python package:**
   ```bash
   cd apps/bank_payment_parser
   bench pip install -e .
   ```

3. **Sync app:**
   ```bash
   bench --site <your-site-name> migrate
   bench --site <your-site-name> clear-cache
   bench restart
   ```

## Getting Your Site Name

To find your site name:
```bash
cd /Users/pratul/frappe-bench
ls sites/ | grep -v "apps.txt\|apps.json\|assets\|common_site_config.json\|excluded_apps.txt"
```

Common site names:
- `sla-test.local` (if you have this)
- `localhost` (if using default)
- Check `sites/` directory for your site folder

## Need Help?

If installation still fails:
1. Check bench logs: `tail -f logs/web.log`
2. Check site logs: `tail -f sites/<site-name>/logs/web.log`
3. Verify Python version: `python3 --version` (should be 3.10+)
4. Verify Frappe version: `bench version`
