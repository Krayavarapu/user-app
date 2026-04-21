from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field, validator


PASSWORD_PATTERN = re.compile(r"^(?=.*\d)(?=.*[^A-Za-z0-9]).+$")


class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    height: Decimal = Field(gt=0)
    weight_lbs: Decimal = Field(gt=0)
    date_of_birth: date
    gender: str = Field(min_length=1, max_length=50)
    user_id: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=128)

    @validator("date_of_birth")
    def date_of_birth_must_not_be_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("date_of_birth cannot be in the future")
        return value

    @validator("password")
    def password_must_have_number_and_special_character(cls, value: str) -> str:
        if not PASSWORD_PATTERN.match(value):
            raise ValueError("password must include at least 1 number and 1 special character")
        return value


class SignupResponse(BaseModel):
    user_id: str
    message: str = "User created successfully"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseModel):
    session_token: str
    user_id: str
    holds: List[str] = Field(default_factory=list)
    restrictions: List[str] = Field(default_factory=list)
