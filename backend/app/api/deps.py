"""Reusable FastAPI dependencies: auth principal extraction + permission guards."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.core.rbac import Permission, has_permission
from backend.app.core.security import decode_token
from backend.app.db.session import get_db
from backend.app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for s in get_db():
        yield s


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_session)
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token, expected_type="access")
        user_id = payload.get("sub")
    except JWTError:
        raise cred_exc
    if not user_id:
        raise cred_exc

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise cred_exc
    return user


def require_permission(permission: Permission):
    """Dependency factory enforcing an RBAC permission on the current user."""

    async def _guard(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"missing permission: {permission.value}",
            )
        return user

    return _guard
