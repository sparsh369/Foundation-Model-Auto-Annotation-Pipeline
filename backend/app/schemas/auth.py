from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from backend.app.core.rbac import Role
from backend.app.schemas.common import ORMModel


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None
    role: Role = Role.VIEWER


class UserOut(ORMModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: Role
    is_active: bool


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str
