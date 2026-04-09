from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth.authentication import authenticate_user, get_user_by_email, register_user
from app.core.auth.dependencies import get_current_user
from app.core.auth.rbac import assign_role_to_user, seed_default_roles
from app.core.auth.sessions.service import SessionService
from app.core.redis_client import get_redis
from app.database import get_db
from app.shared.models.user import User
from app.stream.macropulse.auth_schemas import (
    MacroPulseAuthLogin,
    MacroPulseAuthRegister,
    MacroPulseAuthTokenResponse,
    MacroPulseAuthUserResponse,
)

router = APIRouter(prefix="/auth", tags=["macropulse-auth"])


def _tenant_uuid(tenant_key: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"intelli:macropulse:{tenant_key.strip().lower()}")


async def _get_user_with_roles(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.id == user_id)
    )
    return result.scalar_one_or_none()


def _serialize_user(user: User) -> MacroPulseAuthUserResponse:
    return MacroPulseAuthUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=user.tenant_id,
        tenant_key=user.tenant_key,
        account_type=user.account_type,
        roles=[role.name for role in user.roles],
        is_active=user.is_active,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/register", response_model=MacroPulseAuthUserResponse, status_code=status.HTTP_201_CREATED)
async def register_macropulse_user(
    body: MacroPulseAuthRegister,
    db: AsyncSession = Depends(get_db),
):
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    tenant_key = body.tenant_key.strip()
    user = await register_user(
        db,
        body.email,
        body.password,
        body.full_name,
        tenant_id=_tenant_uuid(tenant_key),
        tenant_key=tenant_key,
        account_type=body.account_type,
    )
    await seed_default_roles(db)
    await assign_role_to_user(db, user.id, body.account_type)
    hydrated = await _get_user_with_roles(db, user.id)
    if hydrated is None:
        raise HTTPException(status_code=500, detail="Unable to load registered user")
    return _serialize_user(hydrated)


@router.post("/login", response_model=MacroPulseAuthTokenResponse)
async def login_macropulse_user(
    body: MacroPulseAuthLogin,
    db: AsyncSession = Depends(get_db),
):
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.account_type not in {"cfo_office", "tenant_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not enabled for MacroPulse tenant login",
        )

    if (user.tenant_key or "").strip().lower() != body.tenant_key.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant key does not match this account",
        )

    hydrated = await _get_user_with_roles(db, user.id)
    if hydrated is None:
        raise HTTPException(status_code=401, detail="User not found")

    redis = await get_redis()
    access_token, refresh_token = await SessionService.create_session(
        db, redis, hydrated, device_name="macropulse-web"
    )
    return MacroPulseAuthTokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_serialize_user(hydrated),
    )


@router.get("/me", response_model=MacroPulseAuthUserResponse)
async def get_macropulse_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    hydrated = await _get_user_with_roles(db, current_user.id)
    if hydrated is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _serialize_user(hydrated)
