import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_macropulse_register_and_login_cfo_office(client: AsyncClient):
    register_resp = await client.post(
        "/api/v1/macropulse/auth/register",
        json={
            "email": "cfo.office@example.com",
            "password": "StrongPass123",
            "full_name": "CFO Office",
            "tenant_key": "demo-in-001",
            "account_type": "cfo_office",
        },
    )
    assert register_resp.status_code == 201
    user = register_resp.json()
    assert user["tenant_key"] == "demo-in-001"
    assert user["account_type"] == "cfo_office"
    assert "cfo_office" in user["roles"]

    login_resp = await client.post(
        "/api/v1/macropulse/auth/login",
        json={
            "email": "cfo.office@example.com",
            "password": "StrongPass123",
            "tenant_key": "demo-in-001",
        },
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["tenant_key"] == "demo-in-001"


async def test_macropulse_login_rejects_wrong_tenant_key(client: AsyncClient):
    await client.post(
        "/api/v1/macropulse/auth/register",
        json={
            "email": "tenant.admin@example.com",
            "password": "StrongPass123",
            "full_name": "Tenant Admin",
            "tenant_key": "tenant-alpha",
            "account_type": "tenant_admin",
        },
    )

    login_resp = await client.post(
        "/api/v1/macropulse/auth/login",
        json={
            "email": "tenant.admin@example.com",
            "password": "StrongPass123",
            "tenant_key": "tenant-beta",
        },
    )
    assert login_resp.status_code == 403


async def test_macropulse_me_returns_tenant_user(client: AsyncClient):
    await client.post(
        "/api/v1/macropulse/auth/register",
        json={
            "email": "tenant.user@example.com",
            "password": "StrongPass123",
            "full_name": "Tenant User",
            "tenant_key": "gcc-demo",
            "account_type": "tenant_admin",
        },
    )
    login_resp = await client.post(
        "/api/v1/macropulse/auth/login",
        json={
            "email": "tenant.user@example.com",
            "password": "StrongPass123",
            "tenant_key": "gcc-demo",
        },
    )
    token = login_resp.json()["access_token"]
    me_resp = await client.get(
        "/api/v1/macropulse/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["tenant_key"] == "gcc-demo"
