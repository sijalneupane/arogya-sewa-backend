"""removed nurse role

Revision ID: b598a6de0af0
Revises: 0c9f9633f0a9
Create Date: 2025-11-13 16:13:01.505966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.enums.role_enum import RoleEnum
from app.utils.alembi_helpers.enum_helper import downgrade_enum, upgrade_enum


# revision identifiers, used by Alembic.
revision: str = 'b598a6de0af0'
down_revision: Union[str, Sequence[str], None] = '0c9f9633f0a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
OLD = ["super_admin", "hospital_admin", "doctor", "patient", "nurse"]
NEW = [e.value for e in RoleEnum]

def upgrade():
    upgrade_enum("role", "role", "role_enum", OLD, NEW)

def downgrade():
    downgrade_enum("role", "role", "role_enum", NEW, OLD)
