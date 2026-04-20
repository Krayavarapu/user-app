from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, validator


class UserBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    height: Decimal = Field(gt=0)
    weight_lbs: Decimal = Field(gt=0)
    date_of_birth: date
    gender: str = Field(min_length=1, max_length=50)
    created_by: date

    @validator("date_of_birth")
    def date_of_birth_must_not_be_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return value


class UserCreate(UserBase):
    user_id: str = Field(min_length=1, max_length=64)


class UserUpdate(UserBase):
    pass


class UserRead(UserBase):
    user_id: str

    class Config:
        orm_mode = True
