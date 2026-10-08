from __future__ import annotations

from typing import Optional

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ExerciseDefinition(Base):
    """One exercise in the curated library. Rows are seeded from app/data/exercise_library/.

    Rows are never deleted (historic plans reference ``exercise_id``); exercises dropped from the
    seed file are marked ``is_active=False`` instead.
    """

    __tablename__ = "exercise_definitions"

    exercise_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    movement_pattern: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    modality: Mapped[str] = mapped_column(String(20), nullable=False)
    laterality: Mapped[str] = mapped_column(String(20), nullable=False)
    measure: Mapped[str] = mapped_column(String(10), nullable=False)
    difficulty: Mapped[int] = mapped_column(Integer, nullable=False)
    primary_muscles: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    secondary_muscles: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    contraindications: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    goal_tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    impact_level: Mapped[str] = mapped_column(String(10), nullable=False)
    default_tempo: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    source_kind: Mapped[str] = mapped_column(String(30), nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    library_version: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())


class ExerciseEquipmentOption(Base):
    """One equipment requirement of an exercise: the set of rows sharing ``option_index`` is an AND
    of equipment; the exercise is doable if ANY of its options is fully owned. An exercise with no
    rows needs no equipment (bodyweight)."""

    __tablename__ = "exercise_equipment_options"

    exercise_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("exercise_definitions.exercise_id", ondelete="CASCADE"),
        primary_key=True,
    )
    option_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipment_id: Mapped[str] = mapped_column(
        String(40),
        ForeignKey("equipment.equipment_id"),
        primary_key=True,
        index=True,
    )
