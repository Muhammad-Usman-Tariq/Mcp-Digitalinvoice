"""Tests for InvoiceService orchestration, validation, and idempotency."""

import uuid
import pytest
import respx
from mcp_digitalinvoice.models.schemas import (
    ConnectAccountInput,
    FillInvoiceInput,
    BuyerInfo,
    InvoiceItem,
)
from mcp_digitalinvoice.services.invoice_service import InvoiceService
from mcp_digitalinvoice.adapter.client import DigitalInvoicingAdapter


@pytest.mark.asyncio
@respx.mock
async def test_connect_account_service(db_session, fake_redis, synthetic_tenant_data):
    base_url = "https://www.digitalinvoicingsoftware.com"
    respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": "fbr_session=test_cookie; Max-Age=7199"},
        json={"user": {}},
    )

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    service = InvoiceService(db=db_session, redis=fake_redis, adapter=adapter)

    inp = ConnectAccountInput(
        email=synthetic_tenant_data["email"],
        password=synthetic_tenant_data["password"],
        name=synthetic_tenant_data["name"],
    )

    res = await service.connect_account(inp)
    assert res.status == "connected"
    assert res.mcp_api_key.startswith("mcp_")
    assert uuid.UUID(res.tenant_id)


@pytest.mark.asyncio
async def test_fill_invoice_validation_needs_info(db_session, fake_redis):
    service = InvoiceService(db=db_session, redis=fake_redis)

    # Input missing buyer province and items
    inp = FillInvoiceInput(
        buyer=BuyerInfo(businessName="Test Co", registrationType="Registered"),
        items=[],
    )

    res = await service.fill_invoice(uuid.uuid4(), inp)
    assert res.status == "needs_info"
    assert "buyer.province" in res.missing_fields
    assert any("items" in f for f in res.missing_fields)
