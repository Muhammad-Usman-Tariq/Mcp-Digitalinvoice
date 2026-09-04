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
async def test_setup_page():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        res = await client.get("/setup")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]
        assert "Digital Invoicing Software MCP Setup" in res.text
        assert 'id="connect-form"' in res.text
        assert 'id="email"' in res.text
        assert 'id="password"' in res.text
        assert 'id="business_name"' in res.text
        assert 'id="tab-claude"' in res.text
        assert 'id="tab-cursor"' in res.text
        assert 'id="tab-windsurf"' in res.text
        assert 'id="tab-antigravity"' in res.text
        assert 'id="tab-openai"' in res.text
        assert 'id="claude-auto-btn"' in res.text
        assert 'id="cursor-auto-btn"' in res.text
        assert "cursor://anysphere.cursor-deeplink/mcp/install" in res.text
        assert "https://claude.ai/customize/connectors" in res.text
        assert "serverUrl" in res.text
        assert "X-MCP-API-Key" in res.text



@pytest.mark.asyncio
async def test_mcp_transport_security_configured():
    from mcp_digitalinvoice.mcp_server.server import mcp
    from mcp_digitalinvoice.config import settings

    expected_hosts = [h.strip() for h in settings.mcp_allowed_hosts.split(",") if h.strip()]
    expected_origins = [f"https://{h}" for h in expected_hosts]

    assert mcp.settings.transport_security is not None
    assert mcp.settings.transport_security.enable_dns_rebinding_protection is True
    assert mcp.settings.transport_security.allowed_hosts == expected_hosts
    assert mcp.settings.transport_security.allowed_origins == expected_origins


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


@pytest.mark.asyncio
async def test_mcp_auth_header_middleware():
    from mcp_digitalinvoice.mcp_server.middleware import (
        MCPAuthHeaderMiddleware,
        mcp_api_key_ctx,
    )

    captured_keys = []

    async def dummy_app(scope, receive, send):
        captured_keys.append(mcp_api_key_ctx.get())

    middleware = MCPAuthHeaderMiddleware(dummy_app)

    # 1. Test X-MCP-API-Key header
    scope1 = {
        "type": "http",
        "headers": [(b"x-mcp-api-key", b"test_key_123")],
    }
    await middleware(scope1, None, None)
    assert captured_keys[-1] == "test_key_123"
    assert mcp_api_key_ctx.get() is None

    # 2. Test x-api-key header
    scope2 = {
        "type": "http",
        "headers": [(b"x-api-key", b"test_key_x_api_key")],
    }
    await middleware(scope2, None, None)
    assert captured_keys[-1] == "test_key_x_api_key"
    assert mcp_api_key_ctx.get() is None

    # 3. Test Authorization Bearer header
    scope3 = {
        "type": "http",
        "headers": [(b"authorization", b"Bearer bearer_key_456")],
    }
    await middleware(scope3, None, None)
    assert captured_keys[-1] == "bearer_key_456"
    assert mcp_api_key_ctx.get() is None

    # 4. Test priority order: X-MCP-API-Key > x-api-key > Authorization
    scope4 = {
        "type": "http",
        "headers": [
            (b"authorization", b"Bearer bearer_key_456"),
            (b"x-api-key", b"x_api_key_override"),
            (b"x-mcp-api-key", b"mcp_key_highest_priority"),
        ],
    }
    await middleware(scope4, None, None)
    assert captured_keys[-1] == "mcp_key_highest_priority"
    assert mcp_api_key_ctx.get() is None

    # 5. Test non-http scope
    scope5 = {"type": "websocket"}
    await middleware(scope5, None, None)
    assert captured_keys[-1] is None


