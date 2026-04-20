"""Rename users.height_ft to users.height.

Revision ID: 20260420_0002
Revises: 20260420_0001
Create Date: 2026-04-20
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260420_0002"
down_revision = "20260420_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    columns = {row[1] for row in connection.execute(sa.text("PRAGMA table_info(users)"))}

    # Supports both states:
    # 1) Existing DBs with height_ft column (migrate to height)
    # 2) Fresh DBs where the base migration already uses height
    if "height" in columns and "height_ft" not in columns:
        return

    if "height_ft" not in columns:
        raise RuntimeError("Expected users.height_ft or users.height to exist before migration")

    op.create_table(
        "users_new",
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

    op.execute(
        """
        INSERT INTO users_new (user_id, first_name, last_name, height, weight_lbs, date_of_birth, gender, created_by)
        SELECT user_id, first_name, last_name, height_ft, weight_lbs, date_of_birth, gender, created_by
        FROM users
        """
    )

    op.drop_table("users")
    op.rename_table("users_new", "users")
    op.create_index(op.f("ix_users_user_id"), "users", ["user_id"], unique=False)


def downgrade() -> None:
    connection = op.get_bind()
    columns = {row[1] for row in connection.execute(sa.text("PRAGMA table_info(users)"))}

    if "height_ft" in columns and "height" not in columns:
        return

    if "height" not in columns:
        raise RuntimeError("Expected users.height or users.height_ft to exist before downgrade")

    op.create_table(
        "users_old",
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("height_ft", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("weight_lbs", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("gender", sa.String(length=50), nullable=False),
        sa.Column("created_by", sa.Date(), nullable=False),
        sa.CheckConstraint("height_ft > 0", name="ck_users_height_ft_positive"),
        sa.CheckConstraint("weight_lbs > 0", name="ck_users_weight_lbs_positive"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.execute(
        """
        INSERT INTO users_old (user_id, first_name, last_name, height_ft, weight_lbs, date_of_birth, gender, created_by)
        SELECT user_id, first_name, last_name, height, weight_lbs, date_of_birth, gender, created_by
        FROM users
        """
    )

    op.drop_table("users")
    op.rename_table("users_old", "users")
    op.create_index(op.f("ix_users_user_id"), "users", ["user_id"], unique=False)
