# Solution: Installation Issues

## ✅ Fixed: Module Not Found Error

The `ModuleNotFoundError: No module named 'bank_payment_parser'` has been fixed by installing the package:

```bash
cd /Users/pratul/frappe-bench
bench pip install -e apps/bank_payment_parser
```

✅ **Package is now installed**

## ❌ Remaining Issue: Database Connection

The current error is:
```
Access denied for user '_eab6ff7e53ea0134'@'localhost' (using password: YES)
```

This is a **database configuration issue**, not an app issue.

## Solutions

### Option 1: Fix Database Connection (Recommended)

1. **Check site configuration:**
   ```bash
   cat sites/sla-test.local/site_config.json
   ```

2. **Verify database credentials:**
   - Check if database user exists
   - Verify password is correct
   - Ensure MariaDB/MySQL is running

3. **Test database connection:**
   ```bash
   # Get database credentials from site_config.json
   mysql -u <db_user> -p <db_name>
   ```

4. **Once database is fixed:**
   ```bash
   bench --site sla-test.local install-app bank_payment_parser
   ```

### Option 2: Install on Different Site

If you have another site with working database:

```bash
# List all sites
ls sites/ | grep -v "apps\|assets\|common_site_config"

# Install on working site
bench --site <working-site-name> install-app bank_payment_parser
```

### Option 3: Manual Installation (Bypass Database Check)

If you just want to verify the app works without database:

1. **App is already installed as Python package** ✅

2. **When database is ready, just run:**
   ```bash
   bench --site <site-name> migrate
   bench --site <site-name> clear-cache
   bench restart
   ```

## Verification

The app structure is correct. Verify with:

```bash
# Check package is installed
cd /Users/pratul/frappe-bench
bench python -c "import bank_payment_parser; print('✅ Installed')"

# Check app files
ls apps/bank_payment_parser/bank_payment_parser/hooks.py
ls apps/bank_payment_parser/bank_payment_parser/services/base_parser.py
ls apps/bank_payment_parser/bank_payment_parser/doctype/bank_payment_advice/bank_payment_advice.json

# All should exist ✅
```

## Next Steps

1. **Fix database connection** for `sla-test.local` site
2. **OR use a different site** with working database
3. **Then run:** `bench --site <site-name> install-app bank_payment_parser`

The app is ready - it just needs a working database connection to complete installation.

## Quick Test (Without Database)

You can test the parser code directly:

```bash
cd /Users/pratul/frappe-bench
bench python

# Then in Python:
from bank_payment_parser.services.parser_factory import get_supported_customers
print(get_supported_customers())
# Should print: ['Hindustan Zinc India Ltd', 'Hindustan Zinc', 'HZL']
```

This confirms the app code is working correctly!
