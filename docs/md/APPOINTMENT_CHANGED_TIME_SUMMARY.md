# Appointment Changed Time Feature - Implementation Summary

## Overview
Refactored the appointment system to track time changes as a separate model with a one-to-many relationship instead of a list field in the Appointment model.

## Changes Made

### 1. New Model: AppointmentChangedTime
**File:** `/app/app/modules/appointment/v1/changed_time_models.py`

- Created a new SQLAlchemy model to track appointment time changes
- Fields:
  - `changed_time_id`: Primary key (12 characters)
  - `appointment_id`: Foreign key to appointment
  - `old_start_time`, `old_end_time`: Original time slot
  - `new_start_time`, `new_end_time`: New time slot
  - `reason`: Optional reason for the change
  - `changed_at`: Timestamp of when the change was made
  - `changed_by_user_id`: Foreign key to the user (doctor) who made the change
  - Includes TimestampMixin for created_at/updated_at

### 2. Updated Appointment Model
**File:** `/app/app/modules/appointment/v1/models.py`

- Removed the `changed_time` field (was `ARRAY(JSONB)`)
- Added `changed_times` relationship: one-to-many with AppointmentChangedTime
- Configured cascade delete for related changed time records

### 3. Schemas
**File:** `/app/app/modules/appointment/v1/changed_time_schema.py`

Created Pydantic schemas:
- `AppointmentChangedTimeCreateSchema`: For creating new records
- `AppointmentChangedTimeUpdateSchema`: For updating existing records
- `AppointmentChangedTimeResponseSchema`: For API responses
- `AppointmentChangedTimeSingleResponse`: Wrapper for single record responses
- `AppointmentChangedTimeListResponse`: Wrapper for list responses

**File:** `/app/app/modules/appointment/v1/schema.py`

- Added `ChangedTimeInfo` schema for nested changed time data in appointment responses
- Updated `AppointmentDetailResponseSchema` to include `changed_times` list
- Modified the model validator to extract and format changed times

### 4. Service Layer
**File:** `/app/app/modules/appointment/v1/changed_time_service.py`

Implemented functions:
- `can_user_view_changed_time()`: Authorization check for viewing
  - Allowed: Superadmin, hospital admin of doctor's hospital, patient, doctor
- `can_user_modify_changed_time()`: Authorization check for modifications
  - Allowed: Only doctors
- `create_changed_time()`: Create a new changed time record
- `get_changed_time_by_id()`: Retrieve a single record
- `get_changed_times_for_appointment()`: Get all changes for an appointment
- `update_changed_time()`: Update an existing record
- `delete_changed_time()`: Delete a record

**File:** `/app/app/modules/appointment/v1/service.py`

- Updated all appointment queries to include `selectinload(Appointment.changed_times)`
- Ensures changed times are loaded when appointments are retrieved

### 5. API Routes
**File:** `/app/app/modules/appointment/v1/changed_time_router.py`

New endpoints:
- `POST /appointment-changed-times`: Create a changed time record (Doctor only)
- `GET /appointment-changed-times/{changed_time_id}`: Get a single record
- `GET /appointment-changed-times/appointment/{appointment_id}`: Get all for an appointment
- `PUT /appointment-changed-times/{changed_time_id}`: Update a record (Doctor only)
- `DELETE /appointment-changed-times/{changed_time_id}`: Delete a record (Doctor only)

All endpoints use the `authorize` dependency and implement custom permission checks.

### 6. Database Migration
**File:** `/app/alembic/versions/c10dc33b11a4_create_appointment_changed_time_table_.py`

- Created `appointment_changed_time` table with all necessary columns and indexes
- Added foreign key constraints with CASCADE delete
- Also added `status` and `booking_fee` columns to doctor table (unrelated but detected)

### 7. Application Registration
**File:** `/app/app/main.py`

- Imported and registered the new `changed_time_router`
- Added to API routes with the `/api/v1` prefix

**File:** `/app/alembic/env.py`

- Added import of `AppointmentChangedTime` model for Alembic to track

## Authorization Rules

### Viewing Changed Times
Users who can view appointment changed time records:
- **Superadmin**: Can view all changed times
- **Hospital Admin**: Can view changed times for appointments with doctors in their hospital
- **Patient**: Can view changed times for their own appointments
- **Doctor**: Can view changed times for their own appointments

### Modifying Changed Times
Only **Doctors** can:
- Create new changed time records
- Update existing changed time records
- Delete changed time records

## API Response Format

When fetching appointments (doctor's own or patient's own), the response includes changed_times:

```json
{
  "message": "Appointment retrieved successfully",
  "data": {
    "appointment_id": "ABC12345",
    "patient": { ... },
    "doctor": { ... },
    "availability": { ... },
    "appointment_date": "2025-12-25",
    "status": "scheduled",
    "changed_times": [
      {
        "changed_time_id": "XYZ123456789",
        "old_start_time": "10:00:00",
        "old_end_time": "10:30:00",
        "new_start_time": "14:00:00",
        "new_end_time": "14:30:00",
        "reason": "Patient requested reschedule",
        "changed_at": "2025-12-20T15:30:00"
      }
    ],
    "created_at": "2025-12-20T10:00:00",
    "updated_at": "2025-12-20T15:30:00"
  }
}
```

## Database Schema

### appointment_changed_time Table
- Primary Key: `changed_time_id` (VARCHAR(12))
- Foreign Keys:
  - `appointment_id` → `appointment.appointment_id` (CASCADE DELETE)
  - `changed_by_user_id` → `user.id` (CASCADE DELETE)
- Indexes: created_time_id, appointment_id, changed_by_user_id
- Timestamps: created_at, updated_at (auto-managed)

## Testing Notes

To test the implementation:
1. A doctor must create an appointment
2. The doctor can then create changed time records for that appointment
3. The patient and doctor can view the changed times when fetching their appointments
4. Only doctors can modify or delete changed time records
5. Hospital admins can view changed times for appointments in their hospital

## Migration Status
✅ Migration created and successfully applied to the database
✅ All tables and relationships created correctly
