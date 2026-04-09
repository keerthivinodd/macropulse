"""
Tenant profile CRUD routes.
POST   /tenant/profile
GET    /tenant/profile/{id}
PUT    /tenant/profile/{id}
DELETE /tenant/profile/{id}
GET    /tenant/profile/{id}/sensitivity
"""
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.stream.macropulse.ingestion.db.session import AsyncSessionLocal
from app.stream.macropulse.ingestion.etl.sensitivity import (
    calculate_sensitivity_matrix,
    get_cached_sensitivity,
)
from app.stream.macropulse.ingestion.models.tenant_profile import TenantProfileModel
from app.stream.macropulse.ingestion.schemas.tenant_profile import TenantProfile

router = APIRouter(prefix="/tenant", tags=["tenant"])


async def _get_fx_rates() -> dict[str, float]:
    """Fetch latest FX rates for sensitivity calculation."""
    from app.stream.macropulse.ingestion.connectors.fx import fetch_fx_rates
    try:
        record = await fetch_fx_rates()
        return {
            "usd_inr": record.usd_inr,
            "aed_inr": record.aed_inr,
            "sar_inr": record.sar_inr,
        }
    except Exception:
        return {"usd_inr": 84.0, "aed_inr": 22.87, "sar_inr": 22.40}


async def _get_latest_brent() -> float:
    """Fetch latest Brent price from DB."""
    from app.stream.macropulse.ingestion.models.commodity_prices import CommodityPrice
    from sqlalchemy import desc
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CommodityPrice)
                .where(CommodityPrice.commodity == "brent_crude")
                .order_by(desc(CommodityPrice.date))
                .limit(1)
            )
            row = result.scalar_one_or_none()
            return row.price_value if row else 80.0
    except Exception:
        return 80.0


@router.post(
    "/profile",
    response_model=TenantProfile,
    summary="Create or upsert tenant profile",
    description="Creates or updates the stored tenant financial profile and notification configuration.",
)
async def create_or_upsert_profile(profile: TenantProfile) -> TenantProfile:
    """Create or upsert a tenant financial profile."""
    async with AsyncSessionLocal() as session:
        existing = await session.get(TenantProfileModel, profile.tenant_id)
        now = datetime.now(timezone.utc)
        payload = profile.model_copy(update={"updated_at": now})
        if existing:
            payload = payload.model_copy(update={"created_at": existing.created_at})
            existing.profile_data = payload.model_dump(mode="json")
            existing.notification_config = payload.notification_config.model_dump(mode="json")
            existing.updated_at = now
        else:
            payload = payload.model_copy(update={"created_at": now})
            session.add(TenantProfileModel(
                tenant_id=payload.tenant_id,
                profile_data=payload.model_dump(mode="json"),
                notification_config=payload.notification_config.model_dump(mode="json"),
            ))
        await session.commit()
    return payload


@router.get(
    "/profile/{tenant_id}",
    response_model=TenantProfile,
    summary="Get tenant profile",
    description="Returns the current tenant financial profile by tenant identifier.",
)
async def get_profile(tenant_id: str) -> TenantProfile:
    """Return tenant profile or 404."""
    async with AsyncSessionLocal() as session:
        row = await session.get(TenantProfileModel, tenant_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant profile not found")
    return TenantProfile(**row.profile_data)


@router.put(
    "/profile/{tenant_id}",
    response_model=TenantProfile,
    summary="Update tenant profile",
    description="Updates the tenant profile and refreshes the cached sensitivity matrix.",
)
async def update_profile(tenant_id: str, profile: TenantProfile) -> TenantProfile:
    """Update tenant profile and recalculate sensitivity matrix."""
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as session:
        row = await session.get(TenantProfileModel, tenant_id)
        if not row or row.is_deleted:
            raise HTTPException(status_code=404, detail="Tenant profile not found")
        updated_profile = profile.model_copy(
            update={"tenant_id": tenant_id, "created_at": row.created_at, "updated_at": now}
        )
        row.profile_data = updated_profile.model_dump(mode="json")
        row.notification_config = updated_profile.notification_config.model_dump(mode="json")
        row.updated_at = now
        await session.commit()

    # Recalculate sensitivity
    fx_rates = await _get_fx_rates()
    brent = await _get_latest_brent()
    calculate_sensitivity_matrix(updated_profile, fx_rates, brent)

    return updated_profile


@router.delete(
    "/profile/{tenant_id}",
    response_model=dict,
    summary="Soft delete tenant profile",
    description="Marks a tenant profile as deleted without removing its historical data.",
)
async def delete_profile(tenant_id: str) -> dict:
    """Soft delete tenant profile."""
    async with AsyncSessionLocal() as session:
        row = await session.get(TenantProfileModel, tenant_id)
        if not row or row.is_deleted:
            raise HTTPException(status_code=404, detail="Tenant profile not found")
        row.is_deleted = True
        row.updated_at = datetime.now(timezone.utc)
        await session.commit()
    return {"status": "deleted", "tenant_id": tenant_id}


@router.get(
    "/profile/{tenant_id}/sensitivity",
    response_model=dict,
    summary="Get tenant sensitivity matrix",
    description="Returns the cached or freshly calculated P&L sensitivity matrix for the tenant.",
)
async def get_sensitivity(tenant_id: str) -> dict[str, Any]:
    """Return sensitivity matrix — from cache or freshly calculated."""
    cached = get_cached_sensitivity(tenant_id)
    if cached:
        return {"source": "cache", "data": cached}

    async with AsyncSessionLocal() as session:
        row = await session.get(TenantProfileModel, tenant_id)
    if not row or row.is_deleted:
        raise HTTPException(status_code=404, detail="Tenant profile not found")

    profile = TenantProfile(**row.profile_data)
    fx_rates = await _get_fx_rates()
    brent = await _get_latest_brent()
    matrix = calculate_sensitivity_matrix(profile, fx_rates, brent)
    return {"source": "calculated", "data": matrix}
