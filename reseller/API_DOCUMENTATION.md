# Reseller API Documentation

## Overview

The Reseller API provides endpoints to manage reseller partners, their commissions, and related statistics.

## Base URL
```
/api/
```

## Authentication
All endpoints require authentication. Include the authorization token in the request headers:
```
Authorization: Bearer <your-token>
```

## Endpoints

### 1. Resellers Management

#### List/Create Resellers
```http
GET /api/resellers/
POST /api/resellers/
```

**GET Parameters:**
- `search`: Search by name, company name, email, or phone
- `ordering`: Sort by name, companyName, joinedDate, totalRevenue, commissionEarned

**POST Body Example:**
```json
{
  "name": "John Doe",
  "companyName": "ABC Solutions",
  "email": "john@abc.com",
  "phone": "+8801712345678",
  "address": "123 Main Street, Dhaka",
  "city": "Dhaka",
  "country": "Bangladesh",
  "defaultCommission": 15.5,
  "status": "active"
}
```

#### Get/Update/Delete Specific Reseller
```http
GET /api/resellers/{id}/
PUT /api/resellers/{id}/
PATCH /api/resellers/{id}/
DELETE /api/resellers/{id}/
```

#### Get Reseller Statistics
```http
GET /api/resellers/{id}/stats/
```

**Response:**
```json
{
  "id": 1,
  "name": "John Doe",
  "companyName": "ABC Solutions",
  "totalClients": 5,
  "totalRevenue": 50000.00,
  "commissionEarned": 7500.00,
  "commission_rate_display": "15.5%",
  "total_unpaid_commissions": 2500.00,
  "total_paid_commissions": 5000.00,
  "recent_commissions": [...],
  "status": "active",
  "joinedDate": "2024-01-15T10:00:00Z",
  "lastActive": "2024-11-05T08:30:00Z"
}
```

#### Update Reseller Status
```http
POST /api/resellers/{id}/status/
```

**Request Body:**
```json
{
  "status": "active" | "inactive" | "suspended"
}
```

#### Get Reseller Commissions
```http
GET /api/resellers/{id}/commissions/
```

**Parameters:**
- `is_paid`: Filter by payment status (true/false)

### 2. Commission Management

#### List/Create Commissions
```http
GET /api/commissions/
POST /api/commissions/
```

**POST Body Example:**
```json
{
  "reseller": 1,
  "client_company": 5,
  "revenue_amount": 10000.00,
  "commission_rate": 15.0,
  "is_paid": false
}
```

#### Get/Update/Delete Specific Commission
```http
GET /api/commissions/{id}/
PUT /api/commissions/{id}/
PATCH /api/commissions/{id}/
DELETE /api/commissions/{id}/
```

#### Mark Commission as Paid
```http
POST /api/commissions/{id}/mark-paid/
```

### 3. Dashboard & Statistics

#### Get Dashboard Statistics
```http
GET /api/dashboard/stats/
```

**Parameters:**
- `status`: Filter by reseller status (active/inactive/suspended/all)

**Response:**
```json
{
  "overview": {
    "total_resellers": 25,
    "active_resellers": 20,
    "inactive_resellers": 3,
    "suspended_resellers": 2,
    "total_revenue": 250000.00,
    "total_commission": 37500.00,
    "unpaid_commissions": 15000.00,
    "paid_commissions": 22500.00,
    "recent_commissions_30d": 45
  },
  "top_resellers": [...]
}
```

## Data Models

### Reseller
```typescript
{
  id: number;
  name: string;
  companyName: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  country: string;
  defaultCommission: number; // Percentage (0-100)
  status: 'active' | 'inactive' | 'suspended';
  totalClients: number;
  totalRevenue: number;
  commissionEarned: number;
  joinedDate: string; // ISO datetime
  lastActive: string; // ISO datetime
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}
```

### ResellerCommission
```typescript
{
  id: number;
  reseller: number; // Reseller ID
  reseller_name: string; // Read-only
  client_company: number; // Company ID
  company_name: string; // Read-only
  revenue_amount: number;
  commission_rate: number; // Percentage
  commission_amount: number; // Auto-calculated
  is_paid: boolean;
  paid_date: string | null; // ISO datetime
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}
```

## Error Responses

### Validation Error (400)
```json
{
  "field_name": ["Error message"]
}
```

### Not Found (404)
```json
{
  "error": "Reseller not found"
}
```

### Server Error (500)
```json
{
  "error": "Internal server error message"
}
```

## Usage Examples

### Create a New Reseller
```javascript
const response = await fetch('/api/resellers/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-token'
  },
  body: JSON.stringify({
    name: 'Jane Smith',
    companyName: 'Smith Technologies',
    email: 'jane@smith.com',
    phone: '+8801987654321',
    address: '456 Business Avenue',
    city: 'Chittagong',
    country: 'Bangladesh',
    defaultCommission: 12.0,
    status: 'active'
  })
});

const reseller = await response.json();
```

### Record a Commission
```javascript
const commission = await fetch('/api/commissions/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer your-token'
  },
  body: JSON.stringify({
    reseller: 1,
    client_company: 3,
    revenue_amount: 15000.00,
    commission_rate: 12.0
  })
});
```

### Get Dashboard Statistics
```javascript
const stats = await fetch('/api/dashboard/stats/?status=active', {
  headers: {
    'Authorization': 'Bearer your-token'
  }
});

const dashboardData = await stats.json();
```

## Notes

1. **Commission Calculation**: Commission amount is automatically calculated based on revenue amount and commission rate.
2. **Phone Validation**: Phone numbers must follow Bangladesh format: `+8801XXXXXXXX`
3. **Email Uniqueness**: Each reseller must have a unique email address.
4. **Status Management**: Resellers can be active, inactive, or suspended.
5. **Automatic Timestamps**: `created_at`, `updated_at`, and `lastActive` are managed automatically.
6. **Search Functionality**: Full-text search available on name, company name, email, and phone fields.