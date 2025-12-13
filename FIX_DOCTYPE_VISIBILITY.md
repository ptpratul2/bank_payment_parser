# Fix: DocType Not Showing in Desk

## Problem
After login, the Bank Payment Advice DocType is not visible (showing 0 DocTypes).

## Root Cause
The app is **built** but **not installed** on the site. DocTypes are created in the database during installation.

## Solution

### Option 1: Install App (Recommended)

**Fix database connection first**, then install:

```bash
# 1. Check database configuration
cat sites/sla-test.local/site_config.json

# 2. Fix database credentials if needed
# Edit: sites/sla-test.local/site_config.json

# 3. Test database connection
mysql -u <db_user> -p <db_name>

# 4. Install app
bench --site sla-test.local install-app bank_payment_parser

# 5. Clear cache
bench --site sla-test.local clear-cache

# 6. Restart bench
bench restart
```

### Option 2: Use Migrate (Alternative)

If database connection works for migrate:

```bash
bench --site sla-test.local migrate
bench --site sla-test.local clear-cache
bench restart
```

### Option 3: Manual Sync (If you have database access)

If you can access the database directly:

1. **Connect to database:**
   ```bash
   mysql -u <db_user> -p <db_name>
   ```

2. **Check if app is in installed_apps:**
   ```sql
   SELECT * FROM `tabDefaultValue` WHERE defkey = 'installed_apps';
   ```

3. **Add app to installed_apps (if not present):**
   ```sql
   UPDATE `tabDefaultValue` 
   SET defvalue = JSON_ARRAY_APPEND(defvalue, '$', 'bank_payment_parser')
   WHERE defkey = 'installed_apps';
   ```

4. **Then run migrate:**
   ```bash
   bench --site sla-test.local migrate
   bench --site sla-test.local clear-cache
   ```

### Option 4: Use Different Site

If you have another site with working database:

```bash
# List sites
ls sites/ | grep -v "apps\|assets\|common_site_config"

# Install on working site
bench --site <working-site-name> install-app bank_payment_parser
```

## Verification

After installation, verify:

1. **Login to Frappe Desk**
2. **Search for "Bank Payment Advice"** in the search bar
3. **Or go to:** Bank Payment Parser > Bank Payment Advice
4. **Should see the list view**

## Quick Check

Check if app is installed:

```bash
bench --site sla-test.local console

# In console:
import frappe
print("Installed apps:", frappe.get_installed_apps())
# Should include 'bank_payment_parser'
```

## Common Issues

### Issue: "Access denied for user"

**Solution:** Fix database credentials in `sites/<site-name>/site_config.json`

### Issue: "App not in apps.txt"

**Solution:** 
```bash
echo "bank_payment_parser" >> sites/apps.txt
```

### Issue: "Module not found"

**Solution:**
```bash
bench pip install -e apps/bank_payment_parser
```

## After Successful Installation

Once installed, you should see:
- ✅ Bank Payment Advice in DocType list
- ✅ Can create new Bank Payment Advice documents
- ✅ Parse PDF functionality available

---

**Note:** The app code is ready and working. The only issue is database connection preventing installation. Once database is fixed, installation will complete and DocTypes will appear.
