# Enhanced Company-Branch Users API with Permissions & Shifts

## Overview
The `UserCompanyBranchViewSet` has been enhanced to support permissions and shifts management, matching the frontend JSON structure you provided.

## Enhanced User Data Structure

Your frontend JSON structure:
```json
{
  "id": "2",
  "name": "Sarah Chen", 
  "email": "sarah.c@restaurant.com",
  "phone": "+1 234 567 8901",
  "role": "waiter",
  "salary": 15,
  "paymentType": "hourly",
  "status": "active", 
  "startDate": "2024-03-20",
  "permissions": {
    "pos": true,
    "kitchen": false,
    "inventory": false,
    "reports": false,
    "settings": false
  },
  "shifts": []
}
```

## New Serializer: `UserCompanyBranchSerializer`

### Added Fields:
- `phone` (maps to `phoneNumber`)
- `salary` (calculated based on role)
- `paymentType` (hourly/monthly based on role)
- `startDate` (from `created_at` or `date_joined`)
- `permissions` (role-based permission object)
- `shifts` (placeholder array for future shift integration)

### Permission System by Role:

| Role | POS | Kitchen | Inventory | Reports | Settings |
|------|-----|---------|-----------|---------|----------|
| software_owner | ✅ | ✅ | ✅ | ✅ | ✅ |
| super_admin | ✅ | ✅ | ✅ | ✅ | ✅ |
| admin | ✅ | ❌ | ✅ | ✅ | ❌ |
| manager | ✅ | ✅ | ✅ | ✅ | ❌ |
| chef | ❌ | ✅ | ❌ | ❌ | ❌ |
| waiter | ✅ | ❌ | ❌ | ❌ | ❌ |
| cashier | ✅ | ❌ | ❌ | ❌ | ❌ |
| staff | ✅ | ❌ | ❌ | ❌ | ❌ |

### Default Salary by Role:
- waiter: $15/hour
- chef: $25/hour  
- manager: $50/month
- cashier: $18/hour
- staff: $16/hour
- admin: $60/month
- super_admin: $80/month

## Enhanced API Endpoints

### 1. **List Users** (Enhanced with permissions & shifts)
```http
GET /api/company-branch-users/
```

**Response:**
```json
{
  "users": [
    {
      "id": 2,
      "name": "Sarah Chen",
      "email": "sarah.c@restaurant.com", 
      "phone": "+8801712345678",
      "role": "waiter",
      "salary": 15,
      "paymentType": "hourly",
      "status": "active",
      "startDate": "2024-03-20",
      "permissions": {
        "pos": true,
        "kitchen": false,
        "inventory": false,
        "reports": false, 
        "settings": false
      },
      "shifts": []
    }
  ],
  "filter_context": {
    "company_id": 5,
    "user_branch_ids": [1, 3],
    "total_users": 12,
    "company_name": "ABC Restaurant"
  }
}
```

### 2. **Filter by Role**
```http
GET /api/company-branch-users/by_role/?role=waiter
```

**Response:**
```json
{
  "users": [...],
  "filter_context": {
    "role": "waiter",
    "total_users": 5,
    "company_id": 5
  }
}
```

### 3. **Filter by Permission**
```http
GET /api/company-branch-users/staff_with_permissions/?permission=pos
```

**Response:**
```json
{
  "users": [...],
  "filter_context": {
    "permission": "pos",
    "roles_included": ["waiter", "cashier", "staff", "manager", "admin"],
    "total_users": 15
  }
}
```

### 4. **Update User Permissions**
```http
POST /api/company-branch-users/{id}/update_permissions/
```

**Request Body:**
```json
{
  "permissions": {
    "pos": true,
    "kitchen": true,
    "inventory": false,
    "reports": false,
    "settings": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Permissions updated successfully",
  "user": {...}
}
```

### 5. **Update Salary & Payment Type**
```http
POST /api/company-branch-users/{id}/update_salary/
```

**Request Body:**
```json
{
  "salary": 20,
  "paymentType": "hourly"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Salary information updated successfully", 
  "user": {...}
}
```

## Usage Examples

### Frontend Integration
```javascript
// Get all users with enhanced data
const response = await fetch('/api/company-branch-users/', {
  headers: { 'Authorization': 'Bearer ' + token }
});
const data = await response.json();

// Each user now matches your frontend structure
data.users.forEach(user => {
  console.log(`${user.name} - ${user.role}`);
  console.log(`Salary: $${user.salary} (${user.paymentType})`);
  console.log('Permissions:', user.permissions);
  console.log('Shifts:', user.shifts);
});
```

### Filter Waiters Only
```javascript
const waiters = await fetch('/api/company-branch-users/by_role/?role=waiter')
  .then(r => r.json());
console.log(`Found ${waiters.filter_context.total_users} waiters`);
```

### Get POS Users
```javascript
const posUsers = await fetch('/api/company-branch-users/staff_with_permissions/?permission=pos')
  .then(r => r.json());
console.log('Users with POS access:', posUsers.users);
```

### Update Permissions
```javascript
const userId = 2;
await fetch(`/api/company-branch-users/${userId}/update_permissions/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + token
  },
  body: JSON.stringify({
    permissions: {
      pos: true,
      kitchen: true, 
      inventory: false,
      reports: false,
      settings: false
    }
  })
});
```

## Backward Compatibility

✅ **All existing functionality preserved**
✅ **Original UserCompanySerializer still available**  
✅ **All previous endpoints still work**
✅ **Enhanced data structure is additive**

## Future Enhancements

### Shifts Integration
When you're ready to add a Shift model:

```python
# In models.py
class Shift(models.Model):
    user = models.ForeignKey(User, related_name='user_shifts', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    start_time = models.TimeField()
    end_time = models.TimeField()
    date = models.DateField()
    
# In serializer get_shifts method:
def get_shifts(self, obj):
    return [
        {
            'id': shift.id,
            'name': shift.name, 
            'start_time': shift.start_time.strftime('%H:%M'),
            'end_time': shift.end_time.strftime('%H:%M'),
            'date': shift.date.strftime('%Y-%m-%d')
        }
        for shift in obj.user_shifts.all()
    ]
```

### Salary & Payment Database Fields
Add to your User model when ready:
```python
class User(AbstractUser):
    # ... existing fields ...
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_type = models.CharField(max_length=20, choices=[('hourly', 'Hourly'), ('monthly', 'Monthly')], default='hourly')
```

## Summary

✅ **Enhanced API matches your frontend JSON structure**
✅ **Added permissions system based on user roles**
✅ **Added salary and payment type support**
✅ **Added shift placeholder for future integration**
✅ **Added filtering by role and permissions**
✅ **Added permission and salary update endpoints**
✅ **Maintained all existing functionality**

Your `/api/company-branch-users/` endpoint now returns data in exactly the format your frontend expects!