from __future__ import annotations

import json
import os
from typing import Any

import redis as redis_lib
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from sqlalchemy import select

from app.stream.macropulse.ingestion.db.session import (
    AsyncSessionLocal,
    get_engine,
    get_engine_url,
    get_sessionmaker,
    region_to_engine_key,
    reset_session_region,
    set_session_region,
)
from app.stream.macropulse.ingestion.models.residency_violations import ResidencyViolation
from app.stream.macropulse.ingestion.models.tenant_profile import TenantProfileModel

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class ResidencyViolationError(PermissionError):
    pass


def _redis():
    return redis_lib.from_url(REDIS_URL)


def cache_tenant_region(tenant_id: str, region: str) -> None:
    try:
        _redis().setex(f"tenant_region:{tenant_id}", 300, region)
    except Exception:
        pass


async def _query_tenant_region_from_db(tenant_id: str) -> str | None:
    for region in ("DEFAULT", "IN", "UAE"):
        try:
            sessionmaker = get_sessionmaker(region)
            async with sessionmaker() as session:
                row = await session.get(TenantProfileModel, tenant_id)
                if row and not row.is_deleted:
                    primary_region = row.profile_data.get("primary_region")
                    if primary_region:
                        cache_tenant_region(tenant_id, primary_region)
                        return primary_region
        except Exception:
            continue
    return None


async def get_tenant_region(tenant_id: str) -> str | None:
    try:
        cached = _redis().get(f"tenant_region:{tenant_id}")
        if cached:
            return cached.decode() if isinstance(cached, bytes) else str(cached)
    except Exception:
        pass
    return await _query_tenant_region_from_db(tenant_id)


async def log_residency_violation(
    tenant_id: str,
    attempted_write_region: str,
    correct_region: str,
    endpoint: str,
) -> None:
    try:
        async with get_sessionmaker("DEFAULT")() as session:
            session.add(
                ResidencyViolation(
                    tenant_id=tenant_id,
                    attempted_write_region=attempted_write_region,
                    correct_region=correct_region,
                    endpoint=endpoint,
                )
            )
            await session.commit()
    except Exception:
        pass


async def _extract_request_json(request: Request) -> dict[str, Any]:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return {}
    body = await request.body()
    request._body = body
    if not body:
        return {}
    try:
        return json.loads(body.decode())
    except Exception:
        return {}


def _body_region(payload: dict[str, Any]) -> str | None:
    return payload.get("primary_region") or payload.get("profile_data", {}).get("primary_region")


def _body_tenant_id(payload: dict[str, Any]) -> str | None:
    return payload.get("tenant_id")


class RegionResidencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        payload = await _extract_request_json(request)
        tenant_id = request.path_params.get("tenant_id") or _body_tenant_id(payload)
        resolved_region = _body_region(payload)
        if not resolved_region and tenant_id:
            resolved_region = await get_tenant_region(tenant_id)

        token = None
        if resolved_region:
            token = set_session_region(resolved_region)
            request.state.region_engine = get_engine(resolved_region)
            request.state.region_engine_url = get_engine_url(resolved_region)
            request.state.correct_region = resolved_region

        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and tenant_id and resolved_region:
            attempted_region = request.headers.get("x-write-region", resolved_region)
            if region_to_engine_key(attempted_region) != region_to_engine_key(resolved_region):
                await log_residency_violation(
                    tenant_id=tenant_id,
                    attempted_write_region=attempted_region,
                    correct_region=resolved_region,
                    endpoint=request.url.path,
                )
                if token is not None:
                    reset_session_region(token)
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Cross-region write blocked by residency policy"},
                )

        try:
            response = await call_next(request)
        finally:
            if token is not None:
                reset_session_region(token)

        return response
