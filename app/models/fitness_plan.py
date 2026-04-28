from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FitnessPlan(Base):
    __tablename__ = "fitness_plans"

    plan_id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.user_id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    goal: Mapped[str] = mapped_column(String(120), nullable=False)
    equipment: Mapped[str] = mapped_column(String(300), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="mock")
    generator_version: Mapped[str] = mapped_column(String(40), nullable=False, default="mock-v1")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    days = relationship("PlanDay", back_populates="plan", cascade="all, delete-orphan")
