# Arogya Sewa Backend API

Arogya Sewa is a healthcare backend built with FastAPI and SQLAlchemy. It supports user onboarding, hospital and doctor management, availability slots, appointment booking and rescheduling, payment workflows, file management, and push/email notifications.

Base API prefix: `/api/v1`

## What This Project Does

- Multi-role healthcare platform backend with roles:
	- `SUPER_ADMIN`
	- `HOSPITAL_ADMIN`
	- `DOCTOR`
	- `PATIENT`
- Manages hospitals, departments, doctors, patients, and appointment lifecycles.
- Supports advance and final payment flows for appointments (including Khalti).
- Supports medical/media file upload and management using Cloudinary.
- Sends push notifications through Firebase Cloud Messaging (FCM).
- Sends email via Mailgun (including webhook signature verification).

## Security Model

### 1. Authentication

- JWT bearer authentication (`Authorization: Bearer <token>`).
- Access token and refresh token generation in [app/core/security.py](app/core/security.py).
- Password hashing/verification via Passlib Argon2.
- Token algorithm: `HS256` (from settings).

### 2. Authorization

- Route-level authorization dependency in [app/core/authorization.py](app/core/authorization.py).
- Authorization checks are path+method based and stored in the `authorization` table.
- Role permission seeds are defined in [app/modules/scripts/create_authorization.py](app/modules/scripts/create_authorization.py).

### 3. Data/Request Security

- Validation handled through FastAPI + Pydantic schemas.
- Global request/response validation handlers in [app/main.py](app/main.py).
- CORS middleware enabled in [app/main.py](app/main.py) for configured origins.

### 4. Integration Security

- Mailgun webhook signature validation in [app/modules/email/v1/router.py](app/modules/email/v1/router.py).
- Khalti requests use server-side secret key headers in [app/modules/payment/v1/khalti_service.py](app/modules/payment/v1/khalti_service.py).

## External Services and Integrations

- PostgreSQL (async SQLAlchemy + asyncpg)
- Cloudinary (file storage and transformations)
- Firebase Admin SDK / FCM (push notifications)
- Khalti Payment Gateway (payment initiation/verification)
- Mailgun (email send and webhook events)

Service initialization on app startup is in [app/main.py](app/main.py):

- Firebase init: [app/core/configuration/firebase_config.py](app/core/configuration/firebase_config.py)
- Cloudinary config: [app/core/configuration/cloudinary_config.py](app/core/configuration/cloudinary_config.py)
- Khalti config: [app/core/configuration/khalti_config.py](app/core/configuration/khalti_config.py)
- Mailgun config: [app/core/configuration/mailgun_config.py](app/core/configuration/mailgun_config.py)

## API Overview and Access Control

Notes:

- `Public` means no auth dependency.
- `Authenticated` means JWT required.
- `AuthZ` means JWT + DB permission check (`Depends(authorize)`).
- Some endpoints also enforce role ownership checks in service/route logic.

### Health

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `GET` | `/api/v1/health` | Health check | Public |

### Auth (`/api/v1/auth`)

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `POST` | `/signup/patient` | Register patient + user | Public |
| `POST` | `/signup/super-admin` | Register super admin | Public |
| `POST` | `/login` | Login and receive access/refresh tokens | Public |
| `GET` | `/me` | Get current authenticated user and optionally update their FCM token via query param | Authenticated |

### Users (`/api/v1/users`)

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `GET` | `/` | List users with pagination/filter | Public |
| `GET` | `/{user_id}` | Get user by ID | Authenticated + AuthZ |
| `PATCH` | `/{user_id}` | Update user details | Authenticated + AuthZ (self or super admin by service logic) |

### Hospitals (`/api/v1/hospital`)

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `POST` | `` | Create hospital + admin association | Authenticated + AuthZ |
| `GET` | `` | List hospitals | Public |
| `GET` | `/my` | Get current hospital admin's hospital | Authenticated |
| `GET` | `/nearest` | Find nearby hospitals by coordinates | Public |
| `GET` | `/{hospital_id}` | Get hospital by ID | Public |
| `PATCH` | `/{hospital_id}` | Update hospital | Authenticated (role/ownership checks in service) |
| `DELETE` | `/{hospital_id}` | Delete hospital | Authenticated (role/ownership checks in service) |

### Doctors (`/api/v1/doctors`)

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `POST` | `` | Create doctor profile + user + email notification | Authenticated + AuthZ |
| `GET` | `` | List doctors with filters and pagination | Public |
| `GET` | `/me` | Get logged-in doctor's profile | Authenticated |
| `GET` | `/hospital/my` | Get doctors for current admin's hospital | Authenticated |
| `GET` | `/hospital/{hospital_id}` | Get doctors for a hospital | Public |
| `GET` | `/{doctor_id}` | Get doctor detail | Public |
| `PATCH` | `/{doctor_id}` | Update doctor profile | Authenticated (role/ownership checks in service) |
| `DELETE` | `/{doctor_id}` | Delete doctor | Authenticated + AuthZ |

### Departments (`/api/v1/departments`)

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `POST` | `` | Create department | Authenticated + AuthZ |
| `GET` | `/hospital/{hospital_id}` | List hospital departments | Public |
| `GET` | `/my` | List departments for current hospital admin | Authenticated + AuthZ |
| `GET` | `/{department_id}` | Get department detail | Public |
| `PATCH` | `/{department_id}` | Update department | Authenticated + AuthZ |
| `DELETE` | `/{department_id}` | Delete department | Authenticated + AuthZ |

### Availabilities (`/api/v1/availabilities`)

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `POST` | `` | Create availability slot | Authenticated + AuthZ |
| `GET` | `` | List availability slots | Public |
| `GET` | `/doctor/{doctor_id}` | List availability for a doctor | Public |
| `GET` | `/{availability_id}` | Get availability detail | Public |
| `PATCH` | `/{availability_id}` | Update availability slot | Authenticated + AuthZ |
| `DELETE` | `/{availability_id}` | Delete availability slot | Authenticated + AuthZ |

### Appointments (`/api/v1/appointments`)

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `POST` | `` | Book appointment | Authenticated + AuthZ (patient profile required) |
| `GET` | `/admin/all` | Super admin view of all appointments | Authenticated + AuthZ + role check |
| `GET` | `/patient/my-appointments` | Patient's own appointments | Authenticated + AuthZ + role check |
| `GET` | `/doctor/my-appointments` | Doctor's own appointments | Authenticated + AuthZ + role check |
| `GET` | `/hospital-admin/appointments` | Hospital admin appointment view | Authenticated + AuthZ + role check |
| `GET` | `/{appointment_id}` | Get appointment detail | Authenticated + AuthZ + ownership/role checks |
| `PATCH` | `/{appointment_id}` | Update appointment | Authenticated + AuthZ (hospital admin/patient by logic) |
| `DELETE` | `/{appointment_id}` | Delete appointment | Authenticated + AuthZ (hospital admin/patient by logic) |

### Appointment Changed Times (`/api/v1/appointment-changed-times`)

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `POST` | `` | Create reschedule history record | Authenticated + AuthZ |
| `GET` | `/{changed_time_id}` | Get specific changed-time record | Authenticated + AuthZ + visibility check |
| `GET` | `/appointment/{appointment_id}` | List changed-time history for an appointment | Authenticated + AuthZ + visibility check |
| `PUT` | `/{changed_time_id}` | Update changed-time record | Authenticated + AuthZ |
| `DELETE` | `/{changed_time_id}` | Delete changed-time record | Authenticated + AuthZ |

### Payments (`/api/v1/payments`)

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `POST` | `/khalti/initiate` | Initiate Khalti advance payment | Authenticated + AuthZ |
| `POST` | `/khalti/verify` | Verify Khalti advance payment | Authenticated + AuthZ |
| `POST` | `/khalti/final/initiate` | Initiate final Khalti payment | Authenticated + AuthZ |
| `POST` | `/khalti/final/verify` | Verify final Khalti payment | Authenticated + AuthZ |
| `POST` | `/cash/record` | Record cash payment | Authenticated + AuthZ |
| `GET` | `/appointment/{appointment_id}` | List payments for an appointment | Authenticated + AuthZ |
| `GET` | `/doctor/my-appointments` | Doctor-specific payment records | Authenticated + AuthZ |
| `GET` | `/hospital-admin/appointments` | Hospital-admin payment records | Authenticated + AuthZ |

### Files (`/api/v1/file`)

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `POST` | `/upload` | Upload file to Cloudinary and save metadata | Authenticated |
| `PATCH` | `/update/{file_id}` | Replace file in Cloudinary | Authenticated |
| `DELETE` | `/delete/{file_id}` | Delete file metadata + Cloudinary asset | Authenticated |

### Notifications (`/api/v1/notifications`)

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `POST` | `/send` | Create notification and send push if token exists | Authenticated |
| `GET` | `/me` | List current user's notifications | Authenticated |
| `PATCH` | `/{notification_id}/read` | Mark notification as read | Authenticated |

### Email (`/api/v1/email`)

| Method | Endpoint | Main Work | Access |
|---|---|---|---|
| `POST` | `/mailgun/test-send` | Send test email via Mailgun | Public |
| `POST` | `/mailgun/webhooks/events` | Process Mailgun webhook events | Public (signature-verified) |

## Key Project Highlights

- Clear role-based architecture with DB-driven authorization policies.
- Rich appointment lifecycle with role-specific filtering endpoints.
- Payment orchestration supports advance and final settlement.
- Notification pipeline stores in DB and pushes to FCM when token exists.
- Modular domain-driven folder layout (`modules/<domain>/v1`).
- Async-first backend stack (FastAPI + Async SQLAlchemy + asyncpg).

## Folder Structure

```text
.
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── authorization.py
│   │   ├── security.py
│   │   ├── config.py
│   │   └── configuration/
│   ├── db/
│   ├── common/
│   │   ├── enums/
│   │   ├── schema/
│   │   └── models/
│   └── modules/
│       ├── auth/v1/
│       ├── user/v1/
│       ├── hospital/v1/
│       ├── doctor/v1/
│       ├── department/v1/
│       ├── availability/v1/
│       ├── appointment/v1/
│       ├── payment/v1/
│       ├── file/v1/
│       ├── notification/v1/
│       ├── email/v1/
│       ├── cloudinary/
│       ├── firebase/
│       └── scripts/
├── alembic/
├── docs/
│   └── db/
├── test/
├── requirements.txt
├── pyproject.toml
└── docker-compose.yml
```

## Important Notes

- Public endpoints above are based on current router dependencies; some may be intended to be restricted later.
- For fully strict RBAC in production, ensure every sensitive route uses both `get_current_user` and `authorize`.
- API docs are available through FastAPI's OpenAPI UI when the app is running (default `/docs`).