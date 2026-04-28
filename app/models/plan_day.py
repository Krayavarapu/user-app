from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PlanDay(Base):
    __tablename__ = "plan_days"
    __table_args__ = (UniqueConstraint("plan_id", "day_number", name="uq_plan_days_plan_day_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[str] = mapped_column(String(64), ForeignKey("fitness_plans.plan_id"), nullable=False, index=True)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    day_label: Mapped[str] = mapped_column(String(40), nullable=False)
    focus: Mapped[str] = mapped_column(String(80), nullable=False)
    workout_json: Mapped[str] = mapped_column(Text, nullable=False)

    plan = relationship("FitnessPlan", back_populates="days")
