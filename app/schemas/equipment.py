from __future__ import annotations

from pydantic import BaseModel


class EquipmentRead(BaseModel):
    equipment_id: str
    name: str
    category: str

    class Config:
        orm_mode = True
