# SetEmployeePayroll API Documentation

## Overview
The `SetEmployeePayroll` model and its APIs allow you to manage employee payroll settings within your restaurant management system. This includes setting base salaries, payment types, and status for employees.

## Model Structure

### SetEmployeePayroll Fields:
- `id`: Auto-generated primary key
- `creator`: ForeignKey to User (who created this payroll setting)
- `company_id`: String field for company identification
- `company`: String field for company name
- `employee`: ForeignKey to User (the employee this payroll is for)
- `salary`: Float field for the base salary amount
- `payment_type`: Choice field ('cash' or 'bank')
- `status`: Choice field ('paid' or 'advance')

## API Endpoints

### 1. SetEmployeePayroll Management
**Base URL**: `/api/employee/payroll/settings/`

#### GET /api/employee/payroll/settings/
- **Description**: List all payroll settings for the company
- **Authentication**: Required (Token)
- **Response**: List of payroll settings with employee details

#### POST /api/employee/payroll/settings/
- **Description**: Create new payroll setting for an employee
- **Authentication**: Required (Token)
- **Request Body**:
```json
{
    "employee": 1,
    "salary": 50000.00,
    "payment_type": "bank",
    "status": "paid"
}
```
- **Response**: Created payroll setting with full details

#### PUT /api/employee/payroll/settings/{id}/
- **Description**: Update existing payroll setting
- **Authentication**: Required (Token)
- **Request Body**: Same as POST

#### DELETE /api/employee/payroll/settings/{id}/
- **Description**: Delete payroll setting
- **Authentication**: Required (Token)

### 2. Custom Actions

#### GET /api/employee/payroll/settings/by_employee/?employee_id={id}
- **Description**: Get payroll setting for a specific employee
- **Authentication**: Required (Token)
- **Parameters**: 
  - `employee_id`: ID of the employee
- **Response**: Payroll setting for the specified employee

#### POST /api/employee/payroll/settings/set_bulk_payroll/
- **Description**: Set payroll for multiple employees at once
- **Authentication**: Required (Token)
- **Request Body**:
```json
{
    "employees": [
        {
            "employee": 1,
            "salary": 50000.00,
            "payment_type": "bank",
            "status": "paid"
        },
        {
            "employee": 2,
            "salary": 35000.00,
            "payment_type": "cash",
            "status": "paid"
        }
    ]
}
```
- **Response**: List of created/updated payroll settings and any errors

### 3. Read-Only List View
**Base URL**: `/api/employee/payroll/settings-list/`

#### GET /api/employee/payroll/settings-list/
- **Description**: Enhanced list view with employee and creator details
- **Authentication**: Required (Token)
- **Query Parameters**:
  - `employee_id`: Filter by employee ID
  - `payment_type`: Filter by payment type ('cash' or 'bank')
  - `status`: Filter by status ('paid' or 'advance')
- **Response**: Enhanced list with nested employee and creator information

## Response Examples

### Single Payroll Setting Response:
```json
{
    "id": 1,
    "creator": 1,
    "creator_name": "Admin User",
    "company_id": "COMP001",
    "company": "Restaurant ABC",
    "employee": 5,
    "employee_name": "John Doe",
    "employee_email": "john.doe@restaurant.com",
    "employee_role": "waiter",
    "salary": 25000.00,
    "payment_type": "bank",
    "status": "paid"
}
```

### List View Response (with details):
```json
[
    {
        "id": 1,
        "creator": 1,
        "creator_details": {
            "id": 1,
            "name": "Admin User",
            "email": "admin@restaurant.com",
            "role": "admin"
        },
        "company_id": "COMP001",
        "company": "Restaurant ABC",
        "employee": 5,
        "employee_details": {
            "id": 5,
            "name": "John Doe",
            "email": "john.doe@restaurant.com",
            "role": "waiter",
            "phone": "+1234567890"
        },
        "salary": 25000.00,
        "payment_type": "bank",
        "status": "paid"
    }
]
```

## Usage Examples

### Setting up payroll for a new employee:
```bash
curl -X POST http://localhost:8000/api/employee/payroll/settings/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employee": 5,
    "salary": 25000.00,
    "payment_type": "bank",
    "status": "paid"
  }'
```

### Getting payroll for a specific employee:
```bash
curl -X GET "http://localhost:8000/api/employee/payroll/settings/by_employee/?employee_id=5" \
  -H "Authorization: Token YOUR_TOKEN"
```

### Bulk payroll setup:
```bash
curl -X POST http://localhost:8000/api/employee/payroll/settings/set_bulk_payroll/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "employees": [
      {
        "employee": 5,
        "salary": 25000.00,
        "payment_type": "bank",
        "status": "paid"
      },
      {
        "employee": 6,
        "salary": 30000.00,
        "payment_type": "cash",
        "status": "paid"
      }
    ]
  }'
```

## Integration with Frontend

The frontend currency system you've implemented can easily integrate with these APIs:

1. **Display salaries in selected currency**: Use the `formatCurrency()` and `convertCurrency()` functions from your CurrencyContext
2. **Form handling**: The salary input in your forms can send the base amount to the API
3. **Real-time updates**: When currency changes, re-fetch and convert the salary displays

### Frontend Integration Example:
```typescript
// In your StaffManagement component
const { formatCurrency, convertCurrency } = useCurrency();

// Fetch payroll data
const fetchPayrollData = async (employeeId: number) => {
  const response = await api.get(`/api/employee/payroll/settings/by_employee/?employee_id=${employeeId}`);
  return response.data;
};

// Display converted salary
const displaySalary = (baseSalary: number) => {
  const convertedAmount = convertCurrency(baseSalary);
  return formatCurrency(convertedAmount);
};
```

## Error Handling

Common error responses:
- **400 Bad Request**: Invalid data or missing required fields
- **401 Unauthorized**: Invalid or missing authentication token
- **404 Not Found**: Payroll setting or employee not found
- **500 Internal Server Error**: Server-side error

## Notes

1. All amounts are stored in the base currency (USD) in the database
2. The `creator`, `company_id`, and `company` fields are automatically set from the authenticated user
3. Each employee can have only one payroll setting per company
4. The bulk operation will update existing payroll settings if they already exist
5. All endpoints are company-scoped - users can only see/modify payroll settings for their own company