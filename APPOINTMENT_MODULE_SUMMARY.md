# Appointment/Booking Module Summary

## Overview
The appointment module allows users to book medical appointments with doctors and manage them with role-based access control.

## Database Schema

### Appointment Table
- **appointment_id**: Primary key (8-char string)
- **patient_id**: Foreign key to patient table
- **doctor_id**: Foreign key to doctor table
- **availability_id**: Foreign key to availability table (unique - one slot = one appointment)
- **booked_by_user_id**: Foreign key to user table (who created the booking)
- **appointment_date**: Date of the appointment
- **reason**: Optional text field for appointment reason
- **notes**: Optional text field for additional notes
- **status**: Enum (scheduled, completed, cancelled)
- **created_at**: Timestamp
- **updated_at**: Timestamp

## API Endpoints

### POST /api/v1/appointments
**Book a new appointment**
- **Access**: Only users with a patient profile
- **Request Body**:
  ```json
  {
    "availability_id": "string",
    "reason": "string (optional)",
    "notes": "string (optional)"
  }
  ```
- **Behavior**:
  - Validates that the availability slot exists and is not booked
  - Checks that the appointment date is in the future
  - Marks the availability slot as booked
  - Creates the appointment record

### GET /api/v1/appointments
**List appointments with role-based filtering**
- **Access**: All authenticated users
- **Query Parameters**:
  - `hospital_id` (super admin only)
  - `doctor_id` (super admin and hospital admin)
  - `patient_name` (super admin only)
  - `appointment_date` (all roles)
  - `skip` (pagination)
  - `limit` (pagination)
  
- **Authorization Logic**:
  - **Super Admin**: Can view all appointments with filters
  - **Hospital Admin**: Can view appointments for doctors in their hospital
  - **Doctor**: Can only view their own appointments
  - **Patient**: Can only view their own appointments

### GET /api/v1/appointments/{appointment_id}
**Get a specific appointment**
- **Access**: Role-based viewing permissions
- **Authorization**:
  - Super admin: Any appointment
  - Hospital admin: Appointments for doctors in their hospital
  - Doctor: Their own appointments only
  - Patient: Their own appointments only

### PATCH /api/v1/appointments/{appointment_id}
**Update an appointment**
- **Access**: Hospital admin and patient only
- **Request Body**:
  ```json
  {
    "reason": "string (optional)",
    "notes": "string (optional)",
    "status": "scheduled|completed|cancelled (optional)"
  }
  ```
- **Authorization**:
  - Hospital admin: Appointments for doctors in their hospital
  - Patient: Their own appointments only

### DELETE /api/v1/appointments/{appointment_id}
**Delete an appointment (cancel booking)**
- **Access**: Hospital admin and patient only
- **Behavior**:
  - Deletes the appointment record
  - Marks the availability slot as not booked (making it available again)
- **Authorization**:
  - Hospital admin: Appointments for doctors in their hospital
  - Patient: Their own appointments only

## Key Features

### 1. Booking Restrictions
- Only patients can book appointments
- Cannot book past dates
- Cannot book already-booked availability slots
- Each availability slot can only have one appointment (unique constraint)

### 2. Role-Based Access Control

#### Super Admin
- View all appointments
- Filter by hospital, doctor, patient name, date
- Cannot update/delete (only hospital admin and patient can)

#### Hospital Admin
- View appointments for doctors in their hospital
- Update appointments for doctors in their hospital
- Delete appointments for doctors in their hospital
- Filter by doctor and date

#### Doctor
- View only their own appointments
- Cannot update or delete
- Filter by date

#### Patient
- View only their own appointments
- Update their own appointments
- Delete their own appointments
- Filter by date

### 3. Availability Integration
- When an appointment is created, the availability slot is marked as booked
- When an appointment is deleted, the availability slot is marked as available again
- Prevents double-booking

## Response Schema

### Appointment Detail Response
```json
{
  "appointment_id": "string",
  "patient": {
    "patient_id": "string",
    "gender": "string",
    "blood_group": "string",
    "user_name": "string",
    "user_email": "string",
    "user_phone": "string"
  },
  "doctor": {
    "doctor_id": "string",
    "specialization_department": "string",
    "experience_years": 0,
    "user_name": "string",
    "user_email": "string"
  },
  "availability": {
    "availability_id": "string",
    "date": "2025-01-01",
    "start_time": "09:00:00",
    "end_time": "10:00:00"
  },
  "appointment_date": "2025-01-01",
  "reason": "string",
  "notes": "string",
  "status": "scheduled",
  "booked_by_user_id": "string",
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

## Files Created

1. `/app/app/modules/appointment/__init__.py`
2. `/app/app/modules/appointment/v1/__init__.py`
3. `/app/app/modules/appointment/v1/models.py` - Database model
4. `/app/app/modules/appointment/v1/schema.py` - Pydantic schemas
5. `/app/app/modules/appointment/v1/service.py` - Business logic
6. `/app/app/modules/appointment/v1/router.py` - API endpoints
7. `/app/alembic/versions/3bd53b59792b_add_appointment_table.py` - Database migration

## Updates Made

1. **app/main.py**: Added appointment router
2. **alembic/env.py**: Added appointment model import for migrations

## Database Migration

Migration has been successfully created and applied:
- Migration ID: `3bd53b59792b`
- Creates `appointment` table with all necessary indexes and foreign keys
- Run with: `alembic upgrade head`

## Testing Recommendations

1. Test booking as a patient
2. Test viewing appointments with different roles
3. Test filtering (hospital, doctor, patient name, date)
4. Test update/delete permissions for each role
5. Test double-booking prevention
6. Test booking past dates (should fail)
7. Test pagination
8. Test availability slot release on appointment deletion
