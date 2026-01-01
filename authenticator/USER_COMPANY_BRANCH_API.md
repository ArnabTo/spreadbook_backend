# User Company Branch API Documentation

## Overview

The `UserCompanyBranchViewSet` provides advanced filtering capabilities for users based on both company membership and branch access. This API is designed for multi-company, multi-branch restaurant management systems.

## Base Endpoint

```
/api/company-branch-users/
```

## Authentication
All endpoints require authentication. The filtering is automatically applied based on the authenticated user's company and branch access.

## Main Endpoints

### 1. List Users by Company and Branch Access

```http
GET /api/company-branch-users/
```

**Functionality:**
- Returns users from the **same company** as the authenticated user
- Further filters to show users who have access to **at least one of the same branches**
- If the user has no branch access, returns all users from the same company

**Response Example:**
```json
{
  "users": [
    {
      "id": 1,
      "name": "John Doe",
      "email": "john@restaurant.com",
      "role": "manager",
      "phoneNumber": "+8801712345678",
      "company": "ABC Restaurant Chain",
      "fullAddress": "123 Main St, Dhaka",
      "city": "Dhaka",
      "status": "active"
    }
  ],
  "filter_context": {
    "company_id": 5,
    "user_branch_ids": [1, 3, 5],
    "total_users": 12,
    "company_name": "ABC Restaurant Chain"
  }
}
```

### 2. Filter Users by Specific Branch

```http
GET /api/company-branch-users/by_branch/?branch_id=3
```

**Parameters:**
- `branch_id` (required): ID of the branch to filter by

**Functionality:**
- Returns users from the same company who have access to the specified branch

**Response Example:**
```json
{
  "users": [
    {
      "id": 2,
      "name": "Jane Smith",
      "email": "jane@restaurant.com",
      "role": "staff",
      "phoneNumber": "+8801987654321"
    }
  ],
  "filter_context": {
    "company_id": 5,
    "company_name": "ABC Restaurant Chain",
    "branch_id": 3,
    "branch_name": "Downtown Branch",
    "total_users": 8
  }
}
```

### 3. Get Branch Managers

```http
GET /api/company-branch-users/branch_managers/
```

**Functionality:**
- Returns users with `role="manager"` from the same company
- Only includes managers who have branch access assigned
- Excludes managers without any branch assignments

**Response Example:**
```json
{
  "managers": [
    {
      "id": 3,
      "name": "Mike Johnson",
      "email": "mike@restaurant.com",
      "role": "manager",
      "phoneNumber": "+8801555123456"
    }
  ],
  "filter_context": {
    "company_id": 5,
    "company_name": "ABC Restaurant Chain",
    "total_managers": 4
  }
}
```

## Use Cases

### 1. **Multi-Branch User Management**
```javascript
// Get all users who can work in the same branches as current user
const response = await fetch('/api/users/company-branch/');
const data = await response.json();
console.log(`Found ${data.filter_context.total_users} users in company`);
```

### 2. **Branch-Specific Staff Lists**
```javascript
// Get all staff for a specific branch
const branchId = 3;
const response = await fetch(`/api/users/company-branch/by_branch/?branch_id=${branchId}`);
const data = await response.json();
console.log(`Branch "${data.filter_context.branch_name}" has ${data.filter_context.total_users} staff members`);
```

### 3. **Manager Directory**
```javascript
// Get all managers with branch responsibilities
const response = await fetch('/api/users/company-branch/branch_managers/');
const data = await response.json();
data.managers.forEach(manager => {
  console.log(`Manager: ${manager.name} (${manager.email})`);
});
```

## Filtering Logic

### Company Filtering
- **Base Rule**: Users must belong to the same company as the authenticated user
- **No Company**: If user has no company assigned, returns empty queryset

### Branch Access Filtering
- **Has Branch Access**: Shows users with overlapping branch access
- **No Branch Access**: Shows all users from the company
- **Intersection Logic**: Uses `branchAccess__id__in` to find users with at least one matching branch

### SQL Query Example
```sql
-- Conceptual SQL for main endpoint
SELECT DISTINCT u.* 
FROM authenticator_user u
JOIN authenticator_user_branchaccess uba ON u.id = uba.user_id
WHERE u.companyId_id = {current_user_company_id}
  AND uba.branch_id IN ({current_user_branch_ids})
```

## Response Context

All endpoints include a `filter_context` object with metadata:

| Field | Description |
|-------|-------------|
| `company_id` | ID of the user's company |
| `company_name` | Name of the user's company |
| `user_branch_ids` | Array of branch IDs the user has access to |
| `total_users` | Number of users returned by the filter |
| `branch_id` | (branch endpoints) Specific branch ID queried |
| `branch_name` | (branch endpoints) Name of the queried branch |

## Error Responses

### Missing Company Association
```json
{
  "error": "User must be associated with a company"
}
```
**Status:** 400 Bad Request

### Missing Branch Parameter
```json
{
  "error": "branch_id parameter is required"
}
```
**Status:** 400 Bad Request

### Authentication Required
```json
{
  "detail": "Authentication credentials were not provided."
}
```
**Status:** 401 Unauthorized

## Integration Examples

### Frontend User Selection Component
```javascript
class BranchUserSelector extends React.Component {
  async loadUsers(branchId = null) {
    const endpoint = branchId 
      ? `/api/users/company-branch/by_branch/?branch_id=${branchId}`
      : '/api/users/company-branch/';
    
    const response = await fetch(endpoint);
    const data = await response.json();
    
    this.setState({
      users: data.users,
      context: data.filter_context
    });
  }
}
```

### Manager Dashboard
```javascript
async function loadManagerDashboard() {
  const [allUsers, managers] = await Promise.all([
    fetch('/api/users/company-branch/').then(r => r.json()),
    fetch('/api/users/company-branch/branch_managers/').then(r => r.json())
  ]);
  
  return {
    totalStaff: allUsers.filter_context.total_users,
    totalManagers: managers.filter_context.total_managers,
    companyName: allUsers.filter_context.company_name
  };
}
```

## Security & Permissions

- **Automatic Filtering**: Users can only see other users from their own company
- **Branch Isolation**: Branch access restrictions are automatically applied
- **Role-Based**: No additional role checks - relies on existing user permissions
- **Data Isolation**: Prevents cross-company data access

## Performance Considerations

- Uses `select_related('companyId')` for efficient company data loading
- Uses `prefetch_related('branchAccess')` for efficient branch data loading
- Applies `distinct()` to prevent duplicate results from ManyToMany joins
- Indexed foreign key relationships for fast filtering