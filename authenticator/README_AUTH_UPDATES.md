# Restaurant Management System - Backend Authentication Updates

## Overview
The backend authenticator has been modified to match the frontend login system expectations for the Restaurant Management System.

## Changes Made

### 1. User Model Updates (`authenticator/models.py`)
- **Added new role choices** to match frontend expectations:
  - `software_owner` - Platform owner with full system access
  - `reseller` - Reseller with limited company management access  
  - `super_admin` - Company super admin with all branch access
  - `admin` - Company admin with multi-branch access
  - `manager` - Branch manager with single branch access
  - `staff`, `waiter`, `chef`, `cashier` - Staff roles with specific permissions

- **Added new fields**:
  - `companyId` - Company identifier for multi-tenant system
  - `resellerId` - Reseller identifier for reseller users
  - `branchAccess` - JSON field storing array of accessible branch IDs
  - `fullName` - Display name matching frontend expectations
  - `username` - Username field (now primary login field instead of email)

### 2. Custom Authentication API (`authenticator/api.py`)
- **New endpoint**: `/api/auth/restaurant-login/`
  - Accepts username/password (matching frontend)
  - Supports demo password authentication:
    - Software Owner: `owner123`
    - Resellers: `reseller123`
    - Super Admin/Admin: `admin123`  
    - Managers: `manager123`
    - Staff roles: `staff123`
    - Fallback: `demo123`
  - Returns JWT tokens + user profile data

- **New endpoint**: `/api/auth/profile/`
  - Returns current user profile data
  - Requires JWT authentication

### 3. Demo Users Management Command
- **Command**: `python manage.py create_demo_users`
- Creates/updates 23+ demo users matching frontend expectations
- Includes users for different companies and roles
- Sets up proper company/branch relationships

### 4. URL Updates (`authenticator/urls.py`)
- Added custom authentication endpoints
- Maintains backward compatibility with existing endpoints

## API Usage

### Login Request
```http
POST /api/auth/restaurant-login/
Content-Type: application/json

{
  "username": "owner",
  "password": "owner123"
}
```

### Login Response
```json
{
  "success": true,
  "user": {
    "id": "user-id",
    "username": "owner",
    "email": "owner@restaurantms.com",
    "fullName": "Software Owner",
    "role": "software_owner",
    "companyId": null,
    "resellerId": null,
    "branchAccess": [],
    "status": "active",
    "lastLogin": "2024-11-01T10:30:00Z",
    "createdAt": "2024-01-01T00:00:00Z"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "expires_in": 604800
}
```

### Profile Request (with JWT)
```http
GET /api/auth/profile/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Setup Instructions

1. **Run migrations** (if not already done):
   ```bash
   python manage.py makemigrations authenticator
   python manage.py migrate
   ```

2. **Create demo users**:
   ```bash
   python manage.py create_demo_users
   ```

3. **Test the login**:
   - Use any of the demo credentials listed in the frontend
   - The backend will now authenticate properly with the frontend

## Demo Users Available

### Platform Level
- **Software Owner**: `owner` / `owner123`
- **Resellers**: `reseller1`, `reseller2`, `reseller3` / `reseller123`

### Company Super Admins
- **Gourmet Palace**: `michael.chen` / `admin123`
- **Quick Bites**: `sarah.johnson` / `admin123`
- **Artisan Coffee**: `emma.williams` / `admin123`
- **Spice Garden**: `raj.patel` / `admin123`
- **Cloud Kitchen**: `david.kim` / `admin123`
- **Pizza Paradise**: `marco.rossi` / `admin123`
- **Sushi Master**: `yuki.tanaka` / `admin123`

### Branch Staff
- **Managers**: `robert.downtown`, `anna.mall`, etc. / `manager123`
- **Staff**: `emily.downtown`, `tom.mall`, etc. / `staff123`

## Frontend Integration

The backend now fully supports the frontend authentication flow:

1. Frontend sends username/password to `/api/auth/restaurant-login/`
2. Backend validates credentials (demo passwords or stored passwords)
3. Backend returns JWT token + user profile
4. Frontend stores token and user data
5. Subsequent API calls use JWT Bearer token authentication

## Backward Compatibility

- All existing API endpoints remain functional
- Legacy role choices are preserved
- Email authentication still works as fallback
- Existing user records are maintained

## Security Notes

- Demo passwords are for development/demo purposes only
- In production, implement proper password policies
- JWT tokens expire after 7 days (configurable)
- Refresh tokens expire after 15 days (configurable)