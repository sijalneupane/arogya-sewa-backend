# User Update API Implementation

## Summary
Created a comprehensive update API for user accounts following the existing project patterns and best practices.

## Changes Made

### 1. Schema Updates ([schema.py](app/modules/user/v1/schema.py))

#### Updated `UserUpdate` Schema
- Added `phone_number` field with validation (10 characters)
- Added field-level validation for `name` (5-14 characters)
- Added field-level validation for `password` (6-20 characters)
- All fields are optional to allow partial updates

#### Added `UserUpdateResponse` Schema
- Standard response format following project conventions
- Includes success message and updated user data
- Uses `UserResponse` for consistent user representation

### 2. Service Layer ([service.py](app/modules/user/v1/service.py))

#### New `update_user()` Function
Implements secure user account updates with:

**Authorization:**
- Super admins can update any user account
- Regular users can only update their own account
- Returns 403 Forbidden for unauthorized access attempts

**Features:**
- Email uniqueness validation (checks if new email is already taken)
- Password hashing when password is updated
- Partial updates (only provided fields are updated)
- Database transaction management (commit/rollback)
- Eager loading of user relationships

**Parameters:**
- `user_id`: Target user to update
- `current_user_id`: ID of user making the request
- `role`: Role of current user (for authorization)
- `email`: New email (optional)
- `name`: New name (optional)
- `phone_number`: New phone number (optional)
- `password`: New password (optional, will be hashed)

### 3. Router Updates ([router.py](app/modules/user/v1/router.py))

#### New PATCH Endpoint: `PATCH /users/{user_id}`

**Features:**
- Protected by authorization middleware
- Requires authentication
- Returns structured response with updated user data
- Supports partial updates (only send fields you want to change)

**Request Example:**
```json
{
  "email": "newemail@example.com",
  "name": "New Name",
  "phone_number": "1234567890",
  "password": "newpassword123"
}
```

**Response Example:**
```json
{
  "message": "User updated successfully",
  "data": {
    "id": "abc12345",
    "email": "newemail@example.com",
    "name": "New Name",
    "phone_number": "1234567890",
    "role": {
      "id": "role_id",
      "role": "PATIENT",
      "description": "Patient role"
    },
    "is_active": true,
    "created_at": "2025-12-17T10:00:00",
    "updated_at": "2025-12-17T11:30:00"
  }
}
```

## Security Features

1. **Authorization Control**: Users can only update their own accounts (except super admins)
2. **Password Hashing**: Passwords are automatically hashed using bcrypt
3. **Email Validation**: Prevents duplicate emails in the system
4. **Field Validation**: Pydantic schemas validate input before processing
5. **Transaction Safety**: Database rollback on errors

## Usage Examples

### Update own profile (as regular user):
```bash
PATCH /api/v1/users/{your_user_id}
Authorization: Bearer {your_token}
Content-Type: application/json

{
  "name": "Updated Name",
  "phone_number": "9876543210"
}
```

### Update any user (as super admin):
```bash
PATCH /api/v1/users/{any_user_id}
Authorization: Bearer {super_admin_token}
Content-Type: application/json

{
  "email": "newemail@example.com",
  "is_active": true
}
```

### Change password:
```bash
PATCH /api/v1/users/{user_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "password": "newSecurePassword123"
}
```

## Error Responses

- **400 Bad Request**: Email already registered
- **403 Forbidden**: Attempting to update another user's account (non-admin)
- **404 Not Found**: User ID not found
- **422 Validation Error**: Invalid input data (wrong format, length, etc.)
- **500 Internal Server Error**: Database or server error

## Testing Recommendations

1. Test updating own account as regular user
2. Test updating other accounts as super admin
3. Test authorization failure (user trying to update another user)
4. Test email uniqueness validation
5. Test password hashing (verify old password no longer works)
6. Test partial updates (only some fields)
7. Test validation errors (invalid email, short name, etc.)
8. Test with all updatable fields simultaneously

## Notes

- The API follows REST conventions using PATCH for partial updates
- Password is never returned in responses (security best practice)
- All timestamps are automatically managed by the database
- The implementation is consistent with other modules in the project (doctor, hospital, etc.)
