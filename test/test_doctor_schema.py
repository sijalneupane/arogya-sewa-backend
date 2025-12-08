#!/usr/bin/env python3
"""
Test script to verify the Doctor module schema validation.
This script tests the serialization of Doctor objects to DoctorResponseSchema.
"""

import sys
import os

sys.path.append("/app")

from datetime import date
from app.modules.doctor.v1.schema import (
    DoctorResponseSchema,
    DoctorWithHospitalResponseSchema,
)
from app.modules.user.v1.schema import UserResponse
from app.common.schema.role import RoleNameDesResponse
from app.common.enums.role_enum import RoleEnum


def test_doctor_schema_validation():
    """Test that the doctor schemas can properly validate objects."""

    # Create a mock role object
    class MockRole:
        def __init__(self):
            self.role = RoleEnum.DOCTOR
            self.description = "Doctor with medical expertise"

    # Create a mock user object (simulating what would come from DB)
    class MockUser:
        def __init__(self):
            self.id = "USR12345"
            self.email = "doctor@hospital.com"
            self.name = "Dr. Jane Smith"
            self.is_active = True
            self.role = MockRole()

    # Create a mock hospital object
    class MockHospital:
        def __init__(self):
            self.hospital_id = "HOSP1234"
            self.name = "Central Hospital"
            self.location = "123 Main Street"

    # Create a mock doctor object (simulating what would come from DB)
    class MockDoctor:
        def __init__(self):
            self.doctor_id = "DOC12345"
            self.specialization_department = "Cardiology"
            self.experience_years = 8
            self.license_certificate = "MD12345"
            self.hospital_id = "HOSP1234"
            self.user = MockUser()
            self.hospital = MockHospital()

    try:
        # Test basic doctor response schema
        mock_doctor = MockDoctor()
        validated_doctor = DoctorResponseSchema.model_validate(mock_doctor)

        print("✅ Basic Doctor schema validation successful!")
        print(f"Doctor ID: {validated_doctor.doctor_id}")
        print(f"Doctor Name: {validated_doctor.user.name}")
        print(f"Specialization: {validated_doctor.specialization_department}")
        print(f"Experience: {validated_doctor.experience_years} years")
        print(f"License: {validated_doctor.license_certificate}")

        # Test doctor with hospital response schema
        validated_doctor_with_hospital = (
            DoctorWithHospitalResponseSchema.model_validate(mock_doctor)
        )

        print("\n✅ Doctor with Hospital schema validation successful!")
        print(f"Doctor Name: {validated_doctor_with_hospital.user.name}")
        print(
            f"Hospital: {validated_doctor_with_hospital.hospital.name if validated_doctor_with_hospital.hospital else 'N/A'}"
        )
        print(
            f"Hospital Location: {validated_doctor_with_hospital.hospital.location if validated_doctor_with_hospital.hospital else 'N/A'}"
        )

        return True

    except Exception as e:
        print(f"❌ Doctor schema validation failed: {e}")
        return False


def test_doctor_without_hospital():
    """Test doctor schema without hospital assignment."""

    class MockRole:
        def __init__(self):
            self.role = RoleEnum.DOCTOR
            self.description = "Doctor with medical expertise"

    class MockUser:
        def __init__(self):
            self.id = "USR67890"
            self.email = "doctor2@example.com"
            self.name = "Dr. John Doe"
            self.is_active = True
            self.role = MockRole()

    class MockDoctorNoHospital:
        def __init__(self):
            self.doctor_id = "DOC67890"
            self.specialization_department = "Dermatology"
            self.experience_years = 5
            self.license_certificate = "MD67890"
            self.hospital_id = None
            self.user = MockUser()
            self.hospital = None

    try:
        mock_doctor = MockDoctorNoHospital()
        validated_doctor = DoctorWithHospitalResponseSchema.model_validate(mock_doctor)

        print("\n✅ Doctor without hospital schema validation successful!")
        print(f"Doctor Name: {validated_doctor.user.name}")
        print(f"Hospital: {validated_doctor.hospital}")  # Should be None

        return True

    except Exception as e:
        print(f"❌ Doctor without hospital schema validation failed: {e}")
        return False


if __name__ == "__main__":
    success1 = test_doctor_schema_validation()
    success2 = test_doctor_without_hospital()

    if success1 and success2:
        print(
            "\n🎉 All doctor schema tests passed! The doctor module is working correctly."
        )
    else:
        print("\n🚨 Some tests failed. There might be additional issues to resolve.")

    sys.exit(0 if (success1 and success2) else 1)
