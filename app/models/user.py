from datetime import date

from sqlalchemy import CheckConstraint, Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("height > 0", name="ck_users_height_positive"),
        CheckConstraint("weight_lbs > 0", name="ck_users_weight_lbs_positive"),
    )

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    height: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    weight_lbs: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(50), nullable=False)
    created_by: Mapped[date] = mapped_column(Date, nullable=False)
