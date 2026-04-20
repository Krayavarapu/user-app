"""Create users table.

Revision ID: 20260420_0001
Revises:
Create Date: 2026-04-20
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260420_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("height", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("weight_lbs", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(length=50), nullable=False),
        sa.Column("created_by", sa.Date(), nullable=False),
        sa.CheckConstraint("height > 0", name="ck_users_height_positive"),
        sa.CheckConstraint("weight_lbs > 0", name="ck_users_weight_lbs_positive"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_users_user_id"), "users", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_user_id"), table_name="users")
    op.drop_table("users")
