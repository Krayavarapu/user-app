from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserProfile(Base):
    """Training preferences for one user (1:1 with ``users``).

    Kept apart from ``users`` so account data and training preferences evolve independently. A
    missing row means "use conservative defaults"; there is no backfill. Equipment lives in
    ``user_equipment``, not here.
    """

    __tablename__ = "user_profiles"
    __table_args__ = (
        CheckConstraint("days_per_week BETWEEN 1 AND 7", name="ck_user_profiles_days_per_week"),
        CheckConstraint("session_length_minutes BETWEEN 15 AND 120", name="ck_user_profiles_session_length"),
    )

    user_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True
    )
    experience_level: Mapped[str] = mapped_column(String(20), nullable=False, default="beginner")
    primary_goal: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    days_per_week: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    session_length_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=45)
    # [{"code": "shoulder", "severity": "moderate", "notes": null}, ...]
    limitations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
