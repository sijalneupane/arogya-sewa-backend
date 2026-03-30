"""create payment module and appointment payment fields

Revision ID: d1f7a1c2b3e4
Revises: 829e1cb3ac29
Create Date: 2026-03-29 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "d1f7a1c2b3e4"
down_revision: Union[str, Sequence[str], None] = "829e1cb3ac29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


payment_status_enum_ddl = postgresql.ENUM(
    "Unpaid",
    "Partial",
    "Paid",
    "Refunded",
    name="payment_status_enum",
)

payment_status_enum = postgresql.ENUM(
    "Unpaid",
    "Partial",
    "Paid",
    "Refunded",
    name="payment_status_enum",
    create_type=False,
)

payment_method_enum_ddl = postgresql.ENUM(
    "Khalti",
    "Esewa",
    "Cash",
    name="payment_method_enum",
)

payment_method_enum = postgresql.ENUM(
    "Khalti",
    "Esewa",
    "Cash",
    name="payment_method_enum",
    create_type=False,
)

payment_transaction_status_enum_ddl = postgresql.ENUM(
    "Pending",
    "Success",
    "Failed",
    "Refunded",
    name="payment_transaction_status_enum",
)

payment_transaction_status_enum = postgresql.ENUM(
    "Pending",
    "Success",
    "Failed",
    "Refunded",
    name="payment_transaction_status_enum",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    payment_status_enum_ddl.create(bind, checkfirst=True)
    payment_method_enum_ddl.create(bind, checkfirst=True)
    payment_transaction_status_enum_ddl.create(bind, checkfirst=True)

    op.add_column(
        "appointment",
        sa.Column("total_amount", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "appointment",
        sa.Column("paid_amount", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "appointment",
        sa.Column("due_amount", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "appointment",
        sa.Column(
            "payment_status",
            payment_status_enum,
            nullable=False,
            server_default="Unpaid",
        ),
    )

    op.create_table(
        "payment",
        sa.Column("payment_id", sa.String(length=12), nullable=False),
        sa.Column("appointment_id", sa.String(length=8), nullable=False),
        sa.Column("paid_by_user_id", sa.String(length=8), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("payment_method", payment_method_enum, nullable=False),
        sa.Column(
            "status",
            payment_transaction_status_enum,
            nullable=False,
            server_default="Pending",
        ),
        sa.Column("transaction_id", sa.String(), nullable=True),
        sa.Column("gateway_ref", sa.String(), nullable=True),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointment.appointment_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["paid_by_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("payment_id"),
    )
    op.create_index(
        op.f("ix_payment_appointment_id"), "payment", ["appointment_id"], unique=False
    )
    op.create_index(
        op.f("ix_payment_payment_id"), "payment", ["payment_id"], unique=False
    )

    op.alter_column("appointment", "total_amount", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_payment_payment_id"), table_name="payment")
    op.drop_index(op.f("ix_payment_appointment_id"), table_name="payment")
    op.drop_table("payment")

    op.drop_column("appointment", "payment_status")
    op.drop_column("appointment", "due_amount")
    op.drop_column("appointment", "paid_amount")
    op.drop_column("appointment", "total_amount")

    bind = op.get_bind()
    payment_transaction_status_enum_ddl.drop(bind, checkfirst=True)
    payment_method_enum_ddl.drop(bind, checkfirst=True)
    payment_status_enum_ddl.drop(bind, checkfirst=True)
