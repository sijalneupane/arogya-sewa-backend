-- Arogya Sewa DB schema outline derived from SQLAlchemy ORM models
-- Note: This is a documentation-oriented SQL outline, not an Alembic migration.

CREATE TYPE role_enum AS ENUM (
  'SUPER_ADMIN',
  'HOSPITAL_ADMIN',
  'DOCTOR',
  'PATIENT'
);

CREATE TYPE file_meta_type_enum AS ENUM (
  'image',
  'video',
  'pdf'
);

CREATE TYPE file_type_enum AS ENUM (
  'profile',
  'license',
  'hospital_logo',
  'hospital',
  'hospital_banner',
  'medical_report',
  'prescription',
  'other'
);

CREATE TYPE appointment_status_enum AS ENUM (
  'scheduled',
  'confirmed',
  'inprogress',
  'completed',
  'cancelled',
  'rescheduled'
);

-- Stored values for doctor status based on values_callable: 'Active', 'On Leave', 'On Appointment', 'Inactive'
CREATE TYPE doctor_status_enum AS ENUM (
  'Active',
  'On Leave',
  'On Appointment',
  'Inactive'
);

CREATE TABLE role (
  id VARCHAR(8) PRIMARY KEY,
  role role_enum NOT NULL,
  description VARCHAR,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_role_id ON role (id);

CREATE TABLE authorization (
  id VARCHAR(8) PRIMARY KEY,
  role_id VARCHAR(8) NOT NULL REFERENCES role(id),
  path VARCHAR NOT NULL,
  methods JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_authorization_id ON authorization (id);

CREATE TABLE "user" (
  id VARCHAR(8) PRIMARY KEY,
  name VARCHAR(50) NOT NULL,
  email VARCHAR(100) NOT NULL UNIQUE,
  phone_number VARCHAR(20) NOT NULL,
  password VARCHAR(255) NOT NULL,
  last_login TIMESTAMP,
  is_active BOOLEAN NOT NULL DEFAULT true,
  role_id VARCHAR(8) NOT NULL REFERENCES role(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_user_id ON "user" (id);
CREATE INDEX ix_user_email ON "user" (email);

CREATE TABLE hospital (
  hospital_id VARCHAR(8) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  location VARCHAR(200) NOT NULL,
  latitude FLOAT NOT NULL,
  longitude FLOAT NOT NULL,
  contact_number VARCHAR(15)[] NOT NULL,
  opened_date DATE,
  admin_id VARCHAR(8) NOT NULL UNIQUE REFERENCES "user"(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_hospital_hospital_id ON hospital (hospital_id);

CREATE TABLE department (
  department_id VARCHAR(10) PRIMARY KEY,
  name VARCHAR(150) NOT NULL,
  description TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT true,
  hospital_id VARCHAR(8) NOT NULL REFERENCES hospital(hospital_id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_department_department_id ON department (department_id);
CREATE INDEX ix_department_hospital_id ON department (hospital_id);

CREATE TABLE file (
  file_id VARCHAR(8) PRIMARY KEY,
  public_id VARCHAR NOT NULL UNIQUE,
  file_url VARCHAR NOT NULL,
  meta_type file_meta_type_enum NOT NULL,
  file_type file_type_enum NOT NULL,
  hospital_id VARCHAR(8) REFERENCES hospital(hospital_id),
  user_id VARCHAR(8) NOT NULL REFERENCES "user"(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_file_file_id ON file (file_id);

CREATE TABLE doctor (
  doctor_id VARCHAR(8) PRIMARY KEY,
  experience VARCHAR(255) NOT NULL DEFAULT 'No experience.',
  status doctor_status_enum NOT NULL DEFAULT 'Active',
  bio TEXT,
  booking_fee FLOAT NOT NULL DEFAULT 0.0,
  license_certificate_id VARCHAR(100) UNIQUE REFERENCES file(file_id),
  user_id VARCHAR(8) NOT NULL UNIQUE REFERENCES "user"(id),
  hospital_id VARCHAR(8) REFERENCES hospital(hospital_id),
  department_id VARCHAR(10) REFERENCES department(department_id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_doctor_doctor_id ON doctor (doctor_id);

CREATE TABLE patient (
  patient_id VARCHAR(8) PRIMARY KEY,
  dob DATE NOT NULL,
  gender VARCHAR(10) NOT NULL,
  blood_group VARCHAR(5) NOT NULL,
  user_id VARCHAR(8) NOT NULL UNIQUE REFERENCES "user"(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_patient_patient_id ON patient (patient_id);

CREATE TABLE availability (
  availability_id VARCHAR(8) PRIMARY KEY,
  doctor_id VARCHAR(8) NOT NULL REFERENCES doctor(doctor_id) ON DELETE CASCADE,
  start_date_time TIMESTAMPTZ NOT NULL,
  end_date_time TIMESTAMPTZ NOT NULL,
  note TEXT,
  is_booked BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_availability_availability_id ON availability (availability_id);
CREATE INDEX ix_availability_doctor_id ON availability (doctor_id);
CREATE INDEX ix_availability_is_booked ON availability (is_booked);

CREATE TABLE appointment (
  appointment_id VARCHAR(8) PRIMARY KEY,
  patient_id VARCHAR(8) NOT NULL REFERENCES patient(patient_id) ON DELETE CASCADE,
  doctor_id VARCHAR(8) NOT NULL REFERENCES doctor(doctor_id) ON DELETE CASCADE,
  availability_id VARCHAR(8) NOT NULL UNIQUE REFERENCES availability(availability_id) ON DELETE CASCADE,
  booked_by_user_id VARCHAR(8) NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  reason TEXT,
  notes TEXT,
  status appointment_status_enum NOT NULL DEFAULT 'scheduled',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_appointment_appointment_id ON appointment (appointment_id);
CREATE INDEX ix_appointment_patient_id ON appointment (patient_id);
CREATE INDEX ix_appointment_doctor_id ON appointment (doctor_id);
CREATE INDEX ix_appointment_availability_id ON appointment (availability_id);
CREATE INDEX ix_appointment_booked_by_user_id ON appointment (booked_by_user_id);
CREATE INDEX ix_appointment_status ON appointment (status);

CREATE TABLE appointment_changed_time (
  changed_time_id VARCHAR(12) PRIMARY KEY,
  appointment_id VARCHAR(8) NOT NULL REFERENCES appointment(appointment_id) ON DELETE CASCADE,
  start_date_time TIMESTAMPTZ NOT NULL,
  end_date_time TIMESTAMPTZ NOT NULL,
  reason TEXT,
  changed_at TIMESTAMPTZ NOT NULL,
  changed_by_user_id VARCHAR(8) NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_appointment_changed_time_changed_time_id ON appointment_changed_time (changed_time_id);
CREATE INDEX ix_appointment_changed_time_appointment_id ON appointment_changed_time (appointment_id);
CREATE INDEX ix_appointment_changed_time_changed_by_user_id ON appointment_changed_time (changed_by_user_id);

-- ORM relationship map (not extra SQL constraints):
-- role.users -> user.role
-- role.authorization -> authorization.role
-- user.files -> file.user
-- user.hospital (one-to-one) -> hospital.admin
-- user.doctor (one-to-one) -> doctor.user
-- user.patient (one-to-one) -> patient.user
-- hospital.files -> file.hospital
-- hospital.doctors -> doctor.hospital
-- hospital.departments -> department.hospital
-- department.doctors -> doctor.department
-- file.doctor_license (one-to-one) -> doctor.license_certificate
-- doctor.availabilities -> availability.doctor
-- appointment.changed_times -> appointment_changed_time.appointment
-- appointment_changed_time.changed_by -> user
