# Product Import Excel Template & Documentation

## Overview

This document describes the Excel format for importing products with unit conversion and stock management into the system.

## Column Headers (Accept multiple formats/aliases)

### Basic Information (Minimum Required: Name OR Code)

| Column Names  | Type   | Example           | Required              | Notes               |
| ------------- | ------ | ----------------- | --------------------- | ------------------- |
| `name`        | String | Paracetamol 500mg | ✓ Either name or code | Product name        |
| `code`        | String | PARA-500          | ✓ Either name or code | Product code/SKU    |
| `sku`         | String | SKU123456         | ✗                     | Stock keeping unit  |
| `description` | String | Pain reliever     | ✗                     | Product description |
| `barcode`     | String | 1234567890        | ✗                     | Product barcode     |

### Pricing Information

| Column Names                        | Type    | Example | Required | Notes                    |
| ----------------------------------- | ------- | ------- | -------- | ------------------------ |
| `price` / `unit price`              | Decimal | 50.00   | ✗        | Can include ৳, $, commas |
| `priceSale` / `price sale`          | Decimal | 45.00   | ✗        | Selling price            |
| `regular_price` / `regular price`   | Decimal | 55.00   | ✗        | Regular/MSRP price       |
| `supplier_price` / `supplier price` | Decimal | 35.00   | ✗        | Cost from supplier       |
| `mrp`                               | Decimal | 60.00   | ✗        | Maximum retail price     |

### Stock & Inventory

| Column Names                         | Type    | Example | Required | Notes            |
| ------------------------------------ | ------- | ------- | -------- | ---------------- |
| `quantity` / `in_stock` / `in stock` | Integer | 100     | ✗        | Product quantity |
| `available`                          | Integer | 95      | ✗        | Available stock  |

### Unit Conversion & Location (For StockSummary creation)

| Column Names                                                     | Type           | Example                            | Required | Notes                                                             |
| ---------------------------------------------------------------- | -------------- | ---------------------------------- | -------- | ----------------------------------------------------------------- |
| `unit_conversion_group` / `unit conversion` / `conversion group` | String/Integer | `Medicine Box-Strip-Tablet` or `1` | ✗        | Name or ID of conversion group. If provided, creates StockSummary |
| `location_type` / `location`                                     | String         | `warehouse` or `branch`            | ✗        | Where stock is stored. Use "warehouse" or "branch"                |
| `location_id` / `warehouse id` / `branch id`                     | Integer        | `5`                                | ✗        | ID of warehouse or branch                                         |
| `stock_quantity` / `stock` / `initial stock`                     | Integer        | 500                                | ✗        | Initial stock quantity in base unit                               |

### Classification & Categorization

| Column Names                | Type   | Example     | Required | Notes            |
| --------------------------- | ------ | ----------- | -------- | ---------------- |
| `category`                  | String | Pain Relief | ✗        | Product category |
| `generic_name` / `generic`  | String | Paracetamol | ✗        | Generic/INN name |
| `brand_name` / `brand name` | String | Napa        | ✗        | Brand name       |
| `manufacturer`              | String | Beximco     | ✗        | Manufacturer     |

### Organizational Scope

| Column Names                                            | Type   | Example     | Required | Notes               |
| ------------------------------------------------------- | ------ | ----------- | -------- | ------------------- |
| `companyId` / `company` / `company name` / `company id` | String | Company ABC | ✗        | Company name or ID  |
| `branch` / `branch name` / `branch code`                | String | Branch-01   | ✗        | Branch name or code |

### Additional Fields

| Column Names  | Type    | Example        | Required | Notes                       |
| ------------- | ------- | -------------- | -------- | --------------------------- |
| `unit`        | String  | kg, pcs, liter | ✗        | Product unit of measurement |
| `weight`      | Decimal | 0.5            | ✗        | Weight                      |
| `size`        | String  | Large          | ✗        | Size                        |
| `color`       | String  | Red            | ✗        | Color                       |
| `country`     | String  | Bangladesh     | ✗        | Country of origin           |
| `gender`      | String  | Unisex         | ✗        | Target gender               |
| `publish`     | Boolean | 1 or true      | ✗        | Published status            |
| `taxes`       | Decimal | 15.0           | ✗        | Tax percentage              |
| `dosage_form` | String  | Tablet         | ✗        | Pharmaceutical form         |
| `strength`    | String  | 500mg          | ✗        | Strength/concentration      |

---

## Excel Format Examples

### Example 1: Simple Product (Minimal Required Fields)

```
| name            | code     |
|-----------------|----------|
| Paracetamol 500 | PARA-500 |
| Ibuprofen 400   | IBU-400  |
```

### Example 2: Product with Pricing

```
| name            | code     | priceSale | regular_price | supplier_price |
|-----------------|----------|-----------|---------------|----------------|
| Paracetamol 500 | PARA-500 | 45.00     | 55.00         | 35.00          |
| Ibuprofen 400   | IBU-400  | 60.00     | 75.00         | 40.00          |
```

### Example 3: Product with Stock & Unit Conversion

```
| name            | code     | priceSale | category | unit_conversion_group     | location_type | location_id | stock_quantity |
|-----------------|----------|-----------|----------|---------------------------|---------------|-------------|----------------|
| Paracetamol 500 | PARA-500 | 45.00     | Medicine | Medicine Box-Strip-Tablet | warehouse     | 1           | 5000           |
| Ibuprofen 400   | IBU-400  | 60.00     | Medicine | Ibuprofen Box-Strip-Tab   | branch        | 2           | 2000           |
```

### Example 4: Complete Product (All Common Fields)

```
| name            | code     | priceSale | regular_price | supplier_price | companyId    | category | generic_name     | brand_name | unit_conversion_group     | location_type | location_id | stock_quantity | weight | description                |
|-----------------|----------|-----------|---------------|----------------|-------------|----------|------------------|------------|---------------------------|---------------|-------------|----------------|--------|----------------------------|
| Paracetamol 500 | PARA-500 | 45.00     | 55.00         | 35.00         | Company-ABC | Medicine | Paracetamol      | Napa       | Medicine Box-Strip-Tablet | warehouse     | 1           | 5000           | 0.5    | Pain reliever and fever    |
| Ibuprofen 400   | IBU-400  | 60.00     | 75.00         | 40.00         | Company-ABC | Medicine | Ibuprofen        | Brufen     | Ibuprofen Box-Strip-Tab   | branch        | 2           | 2000           | 0.6    | Anti-inflammatory         |
```

---

## Behavior & Rules

### 1. **Missing Optional Fields**

- **Result**: Product is still created with only the provided fields
- **Example**: If you only provide `name`, `code`, and `priceSale`, only those fields are populated
- **Empty fields are NOT created as null/empty** - they simply aren't set

### 2. **Stock & Unit Conversion Creation**

- **When StockSummary is created**: Must provide ALL of:
  - `unit_conversion_group` (name or ID)
  - `location_type` ("warehouse" or "branch")
  - `location_id` (ID of warehouse/branch)
  - `stock_quantity` (initial quantity)
- **If any is missing**: No StockSummary is created (import continues without error)
- **Location type mapping**:
  - `"warehouse"` → stock stored in warehouse
  - `"branch"` → stock stored in branch

### 3. **Price Formatting**

- **Accepted formats**:
  - `50` → 50.00
  - `50.00` → 50.00
  - `50,000.50` → 50000.50 (commas removed)
  - `৳50` → 50 (currency symbol removed)
  - `$50` → 50 (currency symbol removed)

### 4. **Required Fields Check**

- **At least ONE of these must be provided**:
  - `name` OR `code`
- **If both are missing**: Row is skipped with message "missing both name and code"

### 5. **Foreign Key Lookups**

| Field                   | Lookup Method                                            |
| ----------------------- | -------------------------------------------------------- |
| `companyId`             | By name (case-insensitive) or numeric ID                 |
| `branch`                | By name or code (case-insensitive) or numeric ID         |
| `unit_conversion_group` | By name (case-insensitive) or numeric ID                 |
| `generic_name`          | By name (case-insensitive) - **Auto-creates if missing** |
| `category`              | Exact match, case-sensitive                              |

### 6. **Empty Cells & Nulls**

- **Empty cells**: Treated as no value provided (field not populated)
- **Zero values**: `0` is a valid value (e.g., `0` for price is allowed)
- **No errors for missing optional fields**: Import continues successfully

---

## Step-by-Step Import Process

### Step 1: Prepare Excel File

1. Use column headers from the table above
2. Add one row per product
3. Save as `.xlsx` or `.csv`

### Step 2: Access Django Admin

1. Go to `/admin/products/product/`
2. Click "Import" button

### Step 3: Upload File

1. Select your Excel file
2. Click "Submit" to preview
3. Review import preview
4. Confirm to import

### Step 4: Monitor Results

- Products are created with provided fields
- StockSummary records are created for rows with complete stock data
- Errors are reported per row
- Import continues even if some rows fail

---

## Sample Excel File (Download Template)

### Scenario: Importing Medicine Products to Warehouse

| name                      | code      | priceSale | regular_price | supplier_price | companyId  | category    | generic_name | brand_name | unit_conversion_group     | location_type | location_id | stock_quantity |
| ------------------------- | --------- | --------- | ------------- | -------------- | ---------- | ----------- | ------------ | ---------- | ------------------------- | ------------- | ----------- | -------------- |
| Paracetamol 500mg Tablet  | PARA-500  | 45.00     | 55.00         | 35.00          | ABC Pharma | Pain Relief | Paracetamol  | Napa       | Tablet Box-Strip-Tablet   | warehouse     | 1           | 5000           |
| Ibuprofen 400mg Tablet    | IBU-400   | 60.00     | 75.00         | 40.00          | ABC Pharma | Pain Relief | Ibuprofen    | Brufen     | Tablet Box-Strip-Tablet   | warehouse     | 1           | 3000           |
| Amoxicillin 500mg Capsule | AMOX-500  | 80.00     | 100.00        | 50.00          | ABC Pharma | Antibiotic  | Amoxicillin  | Amoxil     | Capsule Box-Strip-Capsule | warehouse     | 1           | 2000           |
| Cetirizine 10mg Tablet    | CETI-10   | 30.00     | 40.00         | 20.00          | ABC Pharma | Allergy     | Cetirizine   | Zetirizine | Tablet Box-Strip-Tablet   | branch        | 2           | 1000           |
| Vitamin C 1000mg Tablet   | VITC-1000 | 25.00     | 30.00         | 15.00          | ABC Pharma | Vitamins    | Vitamin C    | Ascorbic   | Tablet Box-Strip-Tablet   | warehouse     | 1           | 8000           |

---

## Troubleshooting

| Issue                                      | Cause                          | Solution                                                                   |
| ------------------------------------------ | ------------------------------ | -------------------------------------------------------------------------- |
| Row skipped - "missing both name and code" | Neither name nor code provided | Add at least name or code                                                  |
| StockSummary not created                   | Missing stock data fields      | Provide: unit_conversion_group, location_type, location_id, stock_quantity |
| "object does not exist" error              | Foreign key lookup failed      | Verify company/branch/conversion group exists in the system                |
| Field value not updating                   | Field was empty in Excel       | Ensure no leading/trailing spaces                                          |
| Price shows as 0                           | Invalid price format           | Use numeric format: `50` or `50.00`                                        |

---

## Best Practices

1. ✅ **Always include at least name or code**
2. ✅ **For stock management: provide all 4 stock-related fields**
3. ✅ **Use consistent company/branch names**
4. ✅ **Test with a small batch first** (5-10 products)
5. ✅ **Keep conversion group IDs consistent**
6. ✅ **Avoid empty rows** between data rows
7. ❌ **Don't manually edit generated ID columns**
8. ❌ **Don't leave required stock fields partially filled**

---

## API Equivalent (For Reference)

**Product fields in the system map to these Excel columns:**

```
Product Model Fields:
├── name
├── code
├── sku
├── description
├── price (alias: unit price)
├── priceSale (alias: price sale)
├── regular_price
├── supplier_price
├── mrp
├── quantity (alias: in_stock)
├── available
├── weight
├── size
├── color
├── category
├── generic_name
├── brand_name
├── manufacturer
├── unit
├── country
├── gender
├── publish
├── taxes
├── dosage_form
├── strength
├── companyId
└── branch

StockSummary Fields (Auto-created):
├── unit_conversion_group
├── location_type
├── location_id
└── stock_quantity
```
