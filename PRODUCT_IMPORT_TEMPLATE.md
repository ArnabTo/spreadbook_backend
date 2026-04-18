# Product Import Excel Template & Documentation

## Overview

This document defines the accepted Excel/CSV columns for product import in admin.
It is aligned with current importer behavior in ProductImportResource.

## Important Updates

- Company lookup now supports company code.
- Branch lookup supports branch code and is company-aware when company is provided.
- Location lookup supports warehouse/branch code, name, or numeric ID.
- Generic name is auto-created in database (company-scoped) and assigned to product FK.
- The following fields are optional: stock_quantity, quantity, low_stock_threshold, unit, display_unit, unit_conversion_group, priceSale, supplier_price.

## Header Aliases

Headers are normalized (case-insensitive, spaces/underscores tolerated).

### Scope and Identity

| Canonical Field | Accepted Header Aliases                                               |
| --------------- | --------------------------------------------------------------------- |
| companyId       | companyId, company, company code, company name, company id, companyid |
| branch          | branch, branch name, branch code, branch id, branchid                 |
| code            | code                                                                  |
| name            | name                                                                  |

### Pricing

| Canonical Field | Accepted Header Aliases           |
| --------------- | --------------------------------- |
| price           | price, unit price                 |
| priceSale       | priceSale, price sale, sale price |
| regular_price   | regular price, regular_price      |
| supplier_price  | supplier price, supplier_price    |
| mrp             | mrp                               |

### Stock and Location

| Canonical Field     | Accepted Header Aliases                                                                                |
| ------------------- | ------------------------------------------------------------------------------------------------------ |
| stock_quantity      | stock_quantity, stock quantity, stock, initial stock, stock quanity                                    |
| quantity            | quantity, max quantity, quanitty                                                                       |
| low_stock_threshold | low_stock_threshold, low stock threshold, low stock, low sotkc threshold                               |
| location_type       | location_type, location type, location                                                                 |
| location_id         | location_id, location id, location code, warehouse id, branch id, warehouse code, branch location code |

### Units and Conversion

| Canonical Field       | Accepted Header Aliases                                       |
| --------------------- | ------------------------------------------------------------- |
| unit                  | unit, primary unit, unit name                                 |
| display_unit          | display_unit, display unit, disploy unit                      |
| unit_conversion_group | unit_conversion_group, unit conversion group, unit conversion |

### Classification

| Canonical Field | Accepted Header Aliases             |
| --------------- | ----------------------------------- |
| category        | category                            |
| generic_name    | generic_name, generic, generic name |
| brand_name      | brand_name, brand, brand name       |
| manufacturer    | manufacturer                        |
| dosage_form     | dosage form, dosage_form            |
| strength        | strength                            |

## Lookup Rules

### companyId

Lookup order:

1. company_code (case-insensitive)
2. company name (case-insensitive)
3. legacy companyId field (case-insensitive)
4. numeric primary key

### branch

Lookup order:

1. branch code (case-insensitive)
2. branch name (case-insensitive)
3. numeric primary key

If companyId is present in row, branch lookup is scoped to that company first.

### location_id with location_type

When location_type is warehouse:

1. warehouse code
2. warehouse name
3. numeric primary key

When location_type is branch:

1. branch code
2. branch name
3. numeric primary key

If product company is known, location lookup is scoped to that company.

### generic_name

- If generic_name exists for the company, it is reused.
- If not found, it is created in database and assigned to product.generic_name.
- Creation is company-scoped (same name can exist in different companies).

## Optional Fields Behavior

These fields are optional and can be blank:

- stock_quantity
- quantity
- low_stock_threshold
- unit
- display_unit
- unit_conversion_group
- priceSale
- supplier_price

Behavior when blank:

- Blank optional values are treated as not provided.
- For update imports, blank optional values do not force overwrite for quantity/stock_quantity/low_stock_threshold.
- price and other numeric fields still support string cleanup (commas and currency symbols).

## Stock Record Creation Rules

ProductBranchInventory rows are created after import when stock can be resolved.

- If location_type and location_id are provided and resolved, inventory is created there.
- Otherwise importer falls back to product.warehouse or product.branch if available.
- unit_conversion_group is accepted but not required for inventory row creation.

## Recommended Minimal Columns

For reliable create/update in multi-company setup, use at least:

- companyId
- code
- name

## Practical Templates

### Template A: Basic Product Import

| companyId | code     | name            | priceSale | supplier_price |
| --------- | -------- | --------------- | --------- | -------------- |
| HLBIZ     | MED-0001 | Paracetamol 500 | 45.00     | 35.00          |
| HLBIZ     | MED-0002 | Ibuprofen 400   | 60.00     | 40.00          |

### Template B: With Branch and Location Codes

| companyId | branch      | code     | name            | location_type | location_id | stock_quantity |
| --------- | ----------- | -------- | --------------- | ------------- | ----------- | -------------- |
| HLBIZ     | HLBIZ-BR001 | MED-0001 | Paracetamol 500 | warehouse     | HLBIZ-WH001 | 5000           |
| HLBIZ     | HLBIZ-BR002 | MED-0002 | Ibuprofen 400   | branch        | HLBIZ-BR002 | 2000           |

### Template C: With Generic Name Auto-Create

| companyId | code     | name            | generic_name | category   |
| --------- | -------- | --------------- | ------------ | ---------- |
| HLBIZ     | MED-0101 | Amoxicillin 500 | Amoxicillin  | Antibiotic |
| HLBIZ     | MED-0102 | Cetirizine 10   | Cetirizine   | Allergy    |

## Price Parsing

Accepted examples:

- 50
- 50.00
- 50,000.50
- $50
- EUR 50
- ৳50

## Import Process

1. Prepare xlsx/csv with supported headers.
2. Open admin: /admin/products/product/
3. Click Import and upload file.
4. Verify preview.
5. Confirm import.

## Troubleshooting

| Issue                                | Likely Cause                                                  | Fix                                                                              |
| ------------------------------------ | ------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| company not found                    | Wrong company code/name/id                                    | Verify companyId value against company_code or company name                      |
| branch not found                     | Branch code/name not matched                                  | Provide branch code and companyId together                                       |
| location not found                   | location_type/location_id mismatch                            | Ensure location_type is warehouse or branch and location_id matches code/name/id |
| generic_name duplicated unexpectedly | Different company scope                                       | Confirm companyId in import row                                                  |
| stock rows not created               | No valid location and no fallback warehouse/branch on product | Provide location_type + location_id, or set product branch/warehouse             |

## Best Practices

1. Prefer company code in companyId column.
2. Prefer branch code in branch column.
3. Prefer location code in location_id column.
4. Keep one header style consistently across one file.
5. Test with 5-10 rows before large upload.
6. Avoid trailing empty formatted rows in Excel.
