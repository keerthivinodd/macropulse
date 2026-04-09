from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


MacroPulseAccountType = Literal["cfo_office", "tenant_admin"]


class MacroPulseAuthRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    tenant_key: str = Field(min_length=2, max_length=100)
    account_type: MacroPulseAccountType


class MacroPulseAuthLogin(BaseModel):
    email: EmailStr
    password: str
    tenant_key: str = Field(min_length=2, max_length=100)


class MacroPulseAuthUserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    tenant_id: uuid.UUID | None
    tenant_key: str | None
    account_type: str
    roles: list[str]
    is_active: bool
    last_login: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MacroPulseAuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: MacroPulseAuthUserResponse
