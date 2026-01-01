-- SQL commands to update branch data with proper values
-- Run these in Django shell or database directly

UPDATE company_branch 
SET 
  fullAddress = CASE 
    WHEN fullAddress IS NULL OR fullAddress = '' THEN 
      CONCAT(name, ' Branch, ', COALESCE(city, 'Dhaka'), ', ', COALESCE(country, 'Bangladesh'))
    ELSE fullAddress
  END,
  manager_name = CASE 
    WHEN manager_name IS NULL OR manager_name = '' THEN 
      CONCAT('Manager of ', name)
    ELSE manager_name
  END,
  phoneNumber = CASE 
    WHEN phoneNumber IS NULL OR phoneNumber = '' THEN 
      '01914039647'
    ELSE phoneNumber
  END,
  todaySales = 1500.00,
  monthSales = 45000.00,
  activeOrders = 8,
  activeTables = 12,
  staff = 10
WHERE id IN (1, 3);

-- Alternative: Update specific branches individually
UPDATE company_branch 
SET 
  fullAddress = 'Sector 6, Road 5, Uttara, Dhaka, Bangladesh',
  manager_name = 'John Manager',
  phoneNumber = '01914039647',
  todaySales = 2500.00,
  monthSales = 75000.00,
  activeOrders = 12,
  activeTables = 18,
  staff = 15
WHERE id = 1;

UPDATE company_branch 
SET 
  fullAddress = 'House 20, Road 8, Dhanmondi, Dhaka, Bangladesh', 
  manager_name = 'Sarah Manager',
  phoneNumber = '01914039648',
  todaySales = 1800.00,
  monthSales = 54000.00,
  activeOrders = 9,
  activeTables = 14,
  staff = 12
WHERE id = 3;