# Fix Installation Issues

## Current Status

✅ App structure is correct  
✅ All Python files compile without errors  
✅ App added to `sites/apps.txt`  
❌ Database connection issue (not an app problem)

## Quick Fix Steps

### 1. Find Your Working Site

```bash
cd /Users/pratul/frappe-bench
# List all sites
ls sites/ | grep -v "apps\|assets\|common_site_config"
```

### 2. Install on a Working Site

If you have a working site (one that can connect to database):

```bash
# Replace <working-site> with your actual site name
bench --site <working-site> install-app bank_payment_parser
```

### 3. If Database Connection Fails

The error you're seeing is:
```
Access denied for user '_eab6ff7e53ea0134'@'localhost'
```

This means:
- Database credentials are incorrect, OR
- Database user doesn't have permissions, OR  
- Database server is not running

**Fix database connection first:**

```bash
# Check site config
cat sites/<your-site>/site_config.json

# Try to connect manually
mysql -u <db_user> -p <db_name>
```

### 4. Alternative: Install Without Database Check

If you just want to verify the app structure works:

```bash
cd /Users/pratul/frappe-bench/apps/bank_payment_parser

# Install Python package
bench pip install -e .

# This will install dependencies without database operations
```

### 5. Manual Installation (Bypass Bench)

If `bench install-app` keeps failing due to database:

1. **App is already in apps.txt** ✅ (done)

2. **Install Python dependencies:**
   ```bash
   bench pip install pdfminer.six
   ```

3. **When database is fixed, run:**
   ```bash
   bench --site <site-name> migrate
   bench --site <site-name> clear-cache
   bench restart
   ```

## Verify App Structure

The app structure is correct. Verify with:

```bash
cd /Users/pratul/frappe-bench/apps/bank_payment_parser

# Check key files exist
ls bank_payment_parser/hooks.py
ls bank_payment_parser/modules.txt
ls bank_payment_parser/services/base_parser.py
ls bank_payment_parser/doctype/bank_payment_advice/bank_payment_advice.json

# All should exist ✅
```

## Next Steps

1. **Fix database connection** for your site
2. **Then run:** `bench --site <site-name> install-app bank_payment_parser`
3. **Or wait** until you have a working site with proper database access

The app itself is ready and correct - it's just waiting for a working database connection to install the DocTypes.
