# DB Model Outline

This document summarizes SQLAlchemy ORM models used by the project, including fields, constraints/properties, and relationships.

## Shared Mixin

All models below inherit `TimestampMixin`, which adds:

- `created_at`: `DateTime(timezone=True)`, `nullable=False`, `server_default=func.now()`
- `updated_at`: `DateTime(timezone=True)`, `nullable=False`, `server_default=func.now()`, `onupdate=func.now()`

## Enums

- `RoleEnum`: `SUPER_ADMIN`, `HOSPITAL_ADMIN`, `DOCTOR`, `PATIENT`
- `FileMetaTypeEnum`: `image`, `video`, `pdf`
- `FileTypeEnum`: `profile`, `license`, `hospital_logo`, `hospital`, `hospital_banner`, `medical_report`, `prescription`, `other`
- `DoctorStatusEnum`: `Active`, `On Leave`, `On Appointment`, `Inactive`
- `AppointmentStatusEnum`: `scheduled`, `confirmed`, `inprogress`, `completed`, `cancelled`, `rescheduled`

## Model: Role (`role`)

| Field | Type | Properties |
|---|---|---|
| `id` | `String(8)` | `primary_key=True`, `index=True`, `nullable=False` |
| `role` | `Enum(RoleEnum, name=role_enum)` | `nullable=False` |
| `description` | `String` | `nullable=True` |
| `created_at` | `DateTime(timezone=True)` | inherited |
| `updated_at` | `DateTime(timezone=True)` | inherited |

Relationships:
- `users` -> `User` (one-to-many, `back_populates=role`, `cascade=all, delete`)
- `authorization` -> `Authorization` (one-to-many, `back_populates=role`, `cascade=all, delete`)

## Model: Authorization (`authorization`)

| Field | Type | Properties |
|---|---|---|
| `id` | `String(8)` | `primary_key=True`, `index=True`, `nullable=False` |
| `role_id` | `String(8)` | `ForeignKey(role.id)`, `nullable=False` |
| `path` | `String` | `nullable=False` |
| `methods` | `JSONB` | `nullable=False`, stores `List[str]` |
| `created_at` | `DateTime(timezone=True)` | inherited |
| `updated_at` | `DateTime(timezone=True)` | inherited |

Relationships:
- `role` -> `Role` (many-to-one, `back_populates=authorization`)

## Model: User (`user`)

| Field | Type | Properties |
|---|---|---|
| `id` | `String(8)` | `primary_key=True`, `index=True`, `nullable=False` |
| `name` | `String(50)` | `nullable=False` |
| `email` | `String(100)` | `unique=True`, `index=True`, `nullable=False` |
| `phone_number` | `String(20)` | `nullable=False` |
| `password` | `VARCHAR(255)` | `nullable=False` |
| `last_login` | `DateTime` | `nullable=True` |
| `is_active` | `Boolean` (inferred) | `nullable=False`, `default=True` |
| `role_id` | `String(8)` | `ForeignKey(role.id)`, `nullable=False` |
| `created_at` | `DateTime(timezone=True)` | inherited |
| `updated_at` | `DateTime(timezone=True)` | inherited |

Relationships:
- `role` -> `Role` (many-to-one, `back_populates=users`)
- `files` -> `File` (one-to-many, `back_populates=user`)
- `hospital` -> `Hospital` (one-to-one, `uselist=False`, `back_populates=admin`)
- `doctor` -> `Doctor` (one-to-one, `uselist=False`, `back_populates=user`)
- `patient` -> `Patient` (one-to-one, `uselist=False`, `back_populates=user`)

Derived property:
- `profile_image`: returns first file in `files` where `file_type == FileTypeEnum.PROFILE`

## Model: Hospital (`hospital`)

| Field | Type | Properties |
|---|---|---|
| `hospital_id` | `String(8)` | `primary_key=True`, `index=True`, `nullable=False` |
| `name` | `String(100)` | `nullable=False` |
| `location` | `String(200)` | `nullable=False` |
| `latitude` | `Float` | `nullable=False` |
| `longitude` | `Float` | `nullable=False` |
| `contact_number` | `ARRAY(String(15))` | `nullable=False`, `default=list` |
| `opened_date` | `Date` | `nullable=True` |
| `admin_id` | `String(8)` | `ForeignKey(user.id)`, `unique=True`, `nullable=False` |
| `created_at` | `DateTime(timezone=True)` | inherited |
| `updated_at` | `DateTime(timezone=True)` | inherited |

Relationships:
- `files` -> `File` (one-to-many, `back_populates=hospital`, `cascade=all, delete-orphan`)
- `admin` -> `User` (one-to-one, `back_populates=hospital`)
- `doctors` -> `Doctor` (one-to-many, `back_populates=hospital`)
- `departments` -> `Department` (one-to-many, `back_populates=hospital`, `cascade=all, delete-orphan`)

## Model: Department (`department`)

| Field | Type | Properties |
|---|---|---|
| `department_id` | `String(10)` | `primary_key=True`, `index=True`, `nullable=False` |
| `name` | `String(150)` | `nullable=False` |
| `description` | `Text` | `nullable=False` |
| `is_active` | `Boolean` | `nullable=False`, `default=True` |
| `hospital_id` | `String(8)` | `ForeignKey(hospital.hospital_id, ondelete=CASCADE)`, `index=True`, `nullable=False` |
| `created_at` | `DateTime(timezone=True)` | inherited |
| `updated_at` | `DateTime(timezone=True)` | inherited |

Relationships:
- `hospital` -> `Hospital` (many-to-one, `back_populates=departments`)
- `doctors` -> `Doctor` (one-to-many, `back_populates=department`)

## Model: File (`file`)

| Field | Type | Properties |
|---|---|---|
| `file_id` | `String(8)` | `primary_key=True`, `index=True`, `nullable=False` |
| `public_id` | `String` | `unique=True`, `nullable=False` |
| `file_url` | `String` | `nullable=False` |
| `meta_type` | `Enum(FileMetaTypeEnum, name=file_meta_type_enum)` | `nullable=False` |
| `file_type` | `Enum(FileTypeEnum, name=file_type_enum)` | `nullable=False` |
| `hospital_id` | `String(8)` | `ForeignKey(hospital.hospital_id)`, `nullable=True` |
| `user_id` | `String(8)` | `ForeignKey(user.id)`, `nullable=False` |
| `created_at` | `DateTime(timezone=True)` | inherited |
| `updated_at` | `DateTime(timezone=True)` | inherited |

Relationships:
- `doctor_license` -> `Doctor` (one-to-one, `uselist=False`, `back_populates=license_certificate`)
- `hospital` -> `Hospital` (many-to-one, `back_populates=files`)
- `user` -> `User` (many-to-one, `back_populates=files`)

## Model: Doctor (`doctor`)

| Field | Type | Properties |
|---|---|---|
| `doctor_id` | `String(8)` | `primary_key=True`, `index=True`, `nullable=False` |
| `experience` | `String(255)` | `nullable=False`, `server_default="No experience."` |
| `status` | `Enum(DoctorStatusEnum)` | `nullable=False`, `default=DoctorStatusEnum.ACTIVE` |
| `bio` | `Text` | `nullable=True` |
| `booking_fee` | `Float` (inferred) | `nullable=False`, `default=0.0` |
| `license_certificate_id` | `String(100)` | `ForeignKey(file.file_id)`, `unique=True`, `nullable=True` |
| `user_id` | `String(8)` | `ForeignKey(user.id)`, `unique=True`, `nullable=False` |
| `hospital_id` | `String(8)` | `ForeignKey(hospital.hospital_id)`, `nullable=True` |
| `department_id` | `String(10)` | `ForeignKey(department.department_id, ondelete=SET NULL)`, `nullable=True` |
| `created_at` | `DateTime(timezone=True)` | inherited |
| `updated_at` | `DateTime(timezone=True)` | inherited |

Relationships:
- `license_certificate` -> `File` (one-to-one, `uselist=False`, `back_populates=doctor_license`)
- `user` -> `User` (one-to-one, `back_populates=doctor`)
- `hospital` -> `Hospital` (many-to-one, `back_populates=doctors`)
- `department` -> `Department` (many-to-one, `back_populates=doctors`)
- `availabilities` -> `Availability` (one-to-many, `back_populates=doctor`, `cascade=all, delete-orphan`)

## Model: Patient (`patient`)

| Field | Type | Properties |
|---|---|---|
| `patient_id` | `String(8)` | `primary_key=True`, `index=True`, `nullable=False` |
| `dob` | `Date` | `nullable=False` |
| `gender` | `String(10)` | `nullable=False` |
| `blood_group` | `String(5)` | `nullable=False` |
| `user_id` | `String(8)` | `ForeignKey(user.id)`, `unique=True`, `nullable=False` |
| `created_at` | `DateTime(timezone=True)` | inherited |
| `updated_at` | `DateTime(timezone=True)` | inherited |

Relationships:
- `user` -> `User` (one-to-one, `back_populates=patient`)

## Model: Availability (`availability`)

| Field | Type | Properties |
|---|---|---|
| `availability_id` | `String(8)` | `primary_key=True`, `index=True`, `nullable=False` |
| `doctor_id` | `String(8)` | `ForeignKey(doctor.doctor_id, ondelete=CASCADE)`, `index=True`, `nullable=False` |
| `start_date_time` | `DateTime(timezone=True)` | `nullable=False` |
| `end_date_time` | `DateTime(timezone=True)` | `nullable=False` |
| `note` | `Text` | `nullable=True` |
| `is_booked` | `Boolean` | `nullable=False`, `default=False`, `server_default="false"`, `index=True` |
| `created_at` | `DateTime(timezone=True)` | inherited |
| `updated_at` | `DateTime(timezone=True)` | inherited |

Relationships:
- `doctor` -> `Doctor` (many-to-one, `back_populates=availabilities`)

## Model: Appointment (`appointment`)

| Field | Type | Properties |
|---|---|---|
| `appointment_id` | `String(8)` | `primary_key=True`, `index=True`, `nullable=False` |
| `patient_id` | `String(8)` | `ForeignKey(patient.patient_id, ondelete=CASCADE)`, `index=True`, `nullable=False` |
| `doctor_id` | `String(8)` | `ForeignKey(doctor.doctor_id, ondelete=CASCADE)`, `index=True`, `nullable=False` |
| `availability_id` | `String(8)` | `ForeignKey(availability.availability_id, ondelete=CASCADE)`, `unique=True`, `index=True`, `nullable=False` |
| `booked_by_user_id` | `String(8)` | `ForeignKey(user.id, ondelete=CASCADE)`, `index=True`, `nullable=False` |
| `reason` | `Text` | `nullable=True` |
| `notes` | `Text` | `nullable=True` |
| `status` | `Enum(AppointmentStatusEnum, name=appointment_status_enum)` | `nullable=False`, `default=SCHEDULED`, `server_default='scheduled'`, `index=True` |
| `created_at` | `DateTime(timezone=True)` | inherited |
| `updated_at` | `DateTime(timezone=True)` | inherited |

Relationships:
- `patient` -> `Patient` (many-to-one)
- `doctor` -> `Doctor` (many-to-one)
- `availability` -> `Availability` (many-to-one in ORM usage; effectively one-to-one via unique `availability_id`)
- `booked_by` -> `User` (many-to-one)
- `changed_times` -> `AppointmentChangedTime` (one-to-many, `back_populates=appointment`, `cascade=all, delete-orphan`)

## Model: AppointmentChangedTime (`appointment_changed_time`)

| Field | Type | Properties |
|---|---|---|
| `changed_time_id` | `String(12)` | `primary_key=True`, `index=True`, `nullable=False` |
| `appointment_id` | `String(8)` | `ForeignKey(appointment.appointment_id, ondelete=CASCADE)`, `index=True`, `nullable=False` |
| `start_date_time` | `DateTime(timezone=True)` | `nullable=False` |
| `end_date_time` | `DateTime(timezone=True)` | `nullable=False` |
| `reason` | `Text` | `nullable=True` |
| `changed_at` | `DateTime(timezone=True)` | `nullable=False`, `default=datetime.now(timezone.utc)` |
| `changed_by_user_id` | `String(8)` | `ForeignKey(user.id, ondelete=CASCADE)`, `index=True`, `nullable=False` |
| `created_at` | `DateTime(timezone=True)` | inherited |
| `updated_at` | `DateTime(timezone=True)` | inherited |

Relationships:
- `appointment` -> `Appointment` (many-to-one, `back_populates=changed_times`)
- `changed_by` -> `User` (many-to-one)
