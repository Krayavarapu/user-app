from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Equipment(Base):
    """Catalog of equipment a user can own. Rows are seeded from app/data/exercise_library/.

    Rows are never deleted (``user_equipment`` and, later, exercise definitions reference them);
    equipment dropped from the seed file is marked ``is_active=False`` instead.
    """

    __tablename__ = "equipment"

    equipment_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    aliases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())


class UserEquipment(Base):
    __tablename__ = "user_equipment"

    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    equipment_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("equipment.equipment_id"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
