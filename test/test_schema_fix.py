#!/usr/bin/env python3
"""
Test script to verify the Pydantic schema validation fixes.
This script tests the serialization of Hospital objects to HospitalResponseSchema.
"""

import sys
import os

sys.path.append("/app")

from datetime import date
from app.modules.hospital.v1.schema import HospitalResponseSchema
from app.modules.user.v1.schema import UserResponse
from app.common.schema.role import RoleNameDesResponse
from app.common.enums.role_enum import RoleEnum


def test_schema_validation():
    """Test that the schemas can properly validate objects."""

    # Create a mock user object (simulating what would come from DB)
    class MockUser:
        def __init__(self):
            self.id = "USR12345"
            self.email = "admin@hospital.com"
            self.name = "John Admin"
            self.is_active = True
            self.role = MockRole()

    class MockRole:
        def __init__(self):
            self.role = RoleEnum.HOSPITAL_ADMIN
            self.description = "Hospital Administrator"

    # Create a mock hospital object (simulating what would come from DB)
    class MockHospital:
        def __init__(self):
            self.hospital_id = "HOSP1234"
            self.name = "Central Hospital"
            self.address = "123 Main Street"
            self.contact_number = ["123-456-7890", "987-654-3210"]
            self.opened_date = date(2023, 1, 15)
            self.admin = MockUser()

    try:
        # Test the validation
        mock_hospital = MockHospital()
        validated_hospital = HospitalResponseSchema.model_validate(mock_hospital)

        print("✅ Schema validation successful!")
        print(f"Hospital ID: {validated_hospital.hospital_id}")
        print(f"Hospital Name: {validated_hospital.name}")
        print(f"Admin Name: {validated_hospital.admin.name}")
        print(f"Admin Role: {validated_hospital.admin.role.role}")
        return True

    except Exception as e:
        print(f"❌ Schema validation failed: {e}")
        return False


if __name__ == "__main__":
    success = test_schema_validation()
    if success:
        print("\n🎉 All tests passed! The Pydantic schema fix is working correctly.")
    else:
        print("\n🚨 Tests failed. There might be additional issues to resolve.")
    sys.exit(0 if success else 1)
