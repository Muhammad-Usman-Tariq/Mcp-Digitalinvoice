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


@pytest.mark.asyncio
@respx.mock
async def test_fill_invoice_auto_fetch_rate_when_omitted(
    db_session, fake_redis, synthetic_tenant_data, synthetic_buyer_data, synthetic_item_data
):
    base_url = "https://www.digitalinvoicingsoftware.com"
    remote_id = str(uuid.uuid4())

    respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": "fbr_session=rate_test_cookie; Max-Age=7199"},
        json={
            "user": {
                "company": {
                    "business_name": synthetic_tenant_data["name"],
                    "ntninc": synthetic_tenant_data["ntn"],
                    "province": "Punjab",
                    "address": synthetic_tenant_data["address"],
                }
            }
        },
    )
    rate_route = respx.get(url__startswith=f"{base_url}/api/fbr/pdi/v2/SaleTypeToRate").respond(
        status_code=200, json=[{"ratE_VALUE": 18.0}]
    )
    inv_route = respx.post(f"{base_url}/api/invoices").respond(
        status_code=201, json={"id": remote_id, "status": "draft"}
    )

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    service = InvoiceService(db=db_session, redis=fake_redis, adapter=adapter)

    conn = await service.connect_account(
        ConnectAccountInput(
            email=synthetic_tenant_data["email"],
            password=synthetic_tenant_data["password"],
            name=synthetic_tenant_data["name"],
        )
    )
    tenant_id = uuid.UUID(conn.tenant_id)

    # Item with rate=None and known sale type
    item = dict(synthetic_item_data)
    item["saleType"] = "Goods at standard rate (default)"
    item["rate"] = None

    inp = FillInvoiceInput(buyer=BuyerInfo(**synthetic_buyer_data), items=[InvoiceItem(**item)])
    res = await service.fill_invoice(tenant_id, inp)

    assert res.status == "saved"
    assert rate_route.called  # Tax rate lookup was invoked automatically!


@pytest.mark.asyncio
@respx.mock
async def test_fill_invoice_explicit_rate_bypasses_lookup(
    db_session, fake_redis, synthetic_tenant_data, synthetic_buyer_data, synthetic_item_data
):
    base_url = "https://www.digitalinvoicingsoftware.com"
    remote_id = str(uuid.uuid4())

    respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": "fbr_session=rate_test_cookie; Max-Age=7199"},
        json={
            "user": {
                "company": {
                    "business_name": synthetic_tenant_data["name"],
                    "ntninc": synthetic_tenant_data["ntn"],
                    "province": "Punjab",
                    "address": synthetic_tenant_data["address"],
                }
            }
        },
    )
    rate_route = respx.get(url__startswith=f"{base_url}/api/fbr/pdi/v2/SaleTypeToRate").respond(
        status_code=200, json=[{"ratE_VALUE": 18.0}]
    )
    inv_route = respx.post(f"{base_url}/api/invoices").respond(
        status_code=201, json={"id": remote_id, "status": "draft"}
    )

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    service = InvoiceService(db=db_session, redis=fake_redis, adapter=adapter)

    conn = await service.connect_account(
        ConnectAccountInput(
            email=synthetic_tenant_data["email"],
            password=synthetic_tenant_data["password"],
            name=synthetic_tenant_data["name"],
        )
    )
    tenant_id = uuid.UUID(conn.tenant_id)

    # Item with explicit rate set
    item = dict(synthetic_item_data)
    item["saleType"] = "Goods at standard rate (default)"
    item["rate"] = "18%"

    inp = FillInvoiceInput(buyer=BuyerInfo(**synthetic_buyer_data), items=[InvoiceItem(**item)])
    res = await service.fill_invoice(tenant_id, inp)

    assert res.status == "saved"
    assert not rate_route.called  # Tax rate lookup was NOT called!

