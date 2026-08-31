"""Tests for REST API endpoints and MCP tool implementations."""

import uuid
import pytest
import respx
from httpx import AsyncClient, ASGITransport

from mcp_digitalinvoice.main import app
from mcp_digitalinvoice.database import get_db_session, get_redis_client
from mcp_digitalinvoice.mcp_server.server import (
    fill_invoice as mcp_fill_invoice,
    validate_invoice as mcp_validate_invoice,
)


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


@pytest.mark.asyncio
@respx.mock
async def test_rest_api_connect_and_fill(
    db_session, fake_redis, synthetic_tenant_data, synthetic_buyer_data, synthetic_item_data
):
    base_url = "https://www.digitalinvoicingsoftware.com"
    remote_id = str(uuid.uuid4())

    respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": "fbr_session=api_test_cookie; Max-Age=7199"},
        json={
            "user": {
                "id": 101,
                "company_id": 202,
                "company": {
                    "business_name": synthetic_tenant_data["name"],
                    "ntninc": synthetic_tenant_data["ntn"],
                    "province": synthetic_tenant_data["province"],
                    "address": synthetic_tenant_data["address"],
                }
            }
        },
    )
    respx.post(f"{base_url}/api/invoices").respond(
        status_code=201, json={"id": remote_id, "status": "draft"}
    )

    async def override_get_db():
        yield db_session

    def override_get_redis():
        return fake_redis

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            # 1. Connect Account
            conn_res = await client.post(
                "/api/v1/connect_account",
                json={
                    "email": synthetic_tenant_data["email"],
                    "password": synthetic_tenant_data["password"],
                    "name": synthetic_tenant_data["name"],
                },
            )
            assert conn_res.status_code == 200
            mcp_key = conn_res.json()["mcp_api_key"]

            # 2. Fill Invoice via REST
            fill_res = await client.post(
                "/api/v1/fill_invoice",
                headers={"Authorization": f"Bearer {mcp_key}"},
                json={
                    "buyer": synthetic_buyer_data,
                    "items": [synthetic_item_data],
                },
            )
            assert fill_res.status_code == 200
            assert fill_res.json()["status"] == "saved"
            assert fill_res.json()["remote_invoice_id"] == remote_id
    finally:
        app.dependency_overrides.clear()
