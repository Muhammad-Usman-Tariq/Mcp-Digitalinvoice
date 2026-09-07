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
        assert 'id="toggle-password-btn"' in res.text
        assert 'id="eye-icon-open"' in res.text
        assert 'id="eye-icon-closed"' in res.text
        assert 'id="openai-code"' in res.text
        assert "Replace YOUR_OPENAI_API_KEY with your own OpenAI API key" in res.text
        assert "[Contact us / see developer docs]" not in res.text



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


@pytest.mark.asyncio
@respx.mock
async def test_get_reports_service_and_adapter(
    db_session, fake_redis, synthetic_tenant_data
):
    base_url = "https://www.digitalinvoicingsoftware.com"
    company_id = "comp_12345"

    respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": "fbr_session=api_test_cookie; Max-Age=7199"},
        json={
            "user": {
                "id": 101,
                "email": synthetic_tenant_data["email"],
                "company_id": company_id,
            }
        },
    )

    from mcp_digitalinvoice.services.invoice_service import InvoiceService
    from mcp_digitalinvoice.models.schemas import ConnectAccountInput

    inv_svc = InvoiceService(db=db_session, redis=fake_redis)
    conn_res = await inv_svc.connect_account(
        ConnectAccountInput(
            email=synthetic_tenant_data["email"],
            password=synthetic_tenant_data["password"],
            name=synthetic_tenant_data["name"],
        )
    )
    tenant_id = uuid.UUID(conn_res.tenant_id)

    mock_invoices = [
        {
            "invoice_ref_no": "INV-001",
            "invoice_date": "2026-09-01",
            "buyer_business_name": "Alpha Corp",
            "invoice_items": [
                {
                    "product_description": "Steel Rod",
                    "quantity": 10,
                    "value_sales_excluding_st": 1000,
                    "sales_tax_applicable": 180,
                    "total_value": 1180,
                    "sale_type": "Standard",
                },
                {
                    "product_description": "Iron Sheet",
                    "quantity": 5,
                    "value_sales_excluding_st": 500,
                    "sales_tax_applicable": 90,
                    "total_value": 590,
                    "sale_type": "Standard",
                },
            ],
        },
        {
            "invoice_ref_no": "INV-002",
            "invoice_date": "2026-09-05",
            "buyer_business_name": "Beta LLC",
            "invoice_items": [
                {
                    "product_description": "Copper Wire",
                    "quantity": 2,
                    "value_sales_excluding_st": 300,
                    "sales_tax_applicable": 54,
                    "total_value": 354,
                    "sale_type": "Standard",
                }
            ],
        },
    ]

    respx.get(f"{base_url}/api/invoices?companyId={company_id}").respond(
        status_code=200,
        json=mock_invoices,
    )

    from mcp_digitalinvoice.services.report_service import ReportService
    from mcp_digitalinvoice.models.schemas import ReportsInput

    report_svc = ReportService(db=db_session, redis=fake_redis)

    # 1. Test group_by="none"
    inp_none = ReportsInput(groupBy="none")
    res_none = await report_svc.get_reports(tenant_id, inp_none)
    assert res_none.status == "ok"
    assert res_none.summary.total_groups == 1
    assert res_none.summary.total_items == 3
    assert res_none.summary.total_quantity == 17.0
    assert res_none.summary.total_amount == 1800.0
    assert res_none.summary.total_gst == 324.0
    assert res_none.summary.net_amount == 2124.0

    # 2. Test group_by="customer" with date filter
    inp_filtered = ReportsInput(dateFrom="2026-09-02", groupBy="customer")
    res_filtered = await report_svc.get_reports(tenant_id, inp_filtered)
    assert res_filtered.status == "ok"
    assert res_filtered.summary.total_groups == 1
    assert res_filtered.summary.total_items == 1
    assert res_filtered.summary.total_quantity == 2.0
    assert res_filtered.groups[0].group_key == "Beta LLC"

    # 3. Test invalid group_by
    inp_invalid = ReportsInput(groupBy="invalid_field")
    res_invalid = await report_svc.get_reports(tenant_id, inp_invalid)
    assert res_invalid.status == "failed"
    assert "Invalid groupBy" in res_invalid.error


