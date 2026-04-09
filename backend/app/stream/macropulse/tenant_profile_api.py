from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/tenant", tags=["tenant"])

# In-memory store for now (replace with DB later)
_profiles: dict[str, dict] = {}

class TenantProfileRequest(BaseModel):
    tenant_id: str
    total_loan_amount_cr: float = 100.0
    floating_ratio: float = 0.65
    usd_exposure_m: float = 12.0
    hedge_ratio_pct: float = 45.0
    total_cogs_cr: float = 400.0
    plastic_pct: float = 9.0
    gsec_amount_cr: float = 75.0
    modified_duration: float = 3.8
    primary_currency: str = "INR"
    primary_region: str = "India"

@router.post("/profile")
async def create_profile(body: TenantProfileRequest):
    _profiles[body.tenant_id] = body.model_dump()
    return {"status": "saved", "tenant_id": body.tenant_id}

@router.get("/profile/{tenant_id}")
async def get_profile(tenant_id: str):
    if tenant_id not in _profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _profiles[tenant_id]
