"""Tests for third-party DigitalInvoicingAdapter using respx HTTP mocking."""

import uuid
import pytest
import respx
import httpx
from mcp_digitalinvoice.adapter.client import DigitalInvoicingAdapter
from mcp_digitalinvoice.adapter.exceptions import (
    UpstreamContractError,
    AuthenticationError,
    UpstreamServerError,
)


@pytest.mark.asyncio
@respx.mock
async def test_adapter_login_success(synthetic_tenant_data):
    base_url = "https://www.digitalinvoicingsoftware.com"
    email = synthetic_tenant_data["email"]
    password = synthetic_tenant_data["password"]
    fake_token = f"sess_{uuid.uuid4().hex}"

    respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": f"fbr_session={fake_token}; Path=/; Max-Age=7199; Secure; HttpOnly"},
        json={"user": {"company": {"business_name": synthetic_tenant_data["name"]}}},
    )

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    res = await adapter.login(email, password)

    assert res["cookie"] == fake_token
    assert res["max_age"] == 7199
    assert res["profile"].get("business_name") == synthetic_tenant_data["name"]


@pytest.mark.asyncio
@respx.mock
async def test_adapter_login_auth_failure(synthetic_tenant_data):
    base_url = "https://www.digitalinvoicingsoftware.com"
    respx.post(f"{base_url}/api/auth/login").respond(status_code=401)

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    with pytest.raises(AuthenticationError):
        await adapter.login(synthetic_tenant_data["email"], synthetic_tenant_data["password"])


@pytest.mark.asyncio
@respx.mock
async def test_adapter_create_invoice_success():
    base_url = "https://www.digitalinvoicingsoftware.com"
    remote_id = str(uuid.uuid4())

    respx.post(f"{base_url}/api/invoices").respond(
        status_code=201, json={"id": remote_id, "status": "draft"}
    )

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    res = await adapter.create_or_update_invoice("fake_cookie", {"invoice": {}, "details": []})

    assert res["id"] == remote_id
    assert res["status"] == "draft"


@pytest.mark.asyncio
@respx.mock
async def test_adapter_contract_error_missing_id():
    base_url = "https://www.digitalinvoicingsoftware.com"
    respx.post(f"{base_url}/api/invoices").respond(
        status_code=200, json={"status": "draft"}  # missing mandatory 'id' key
    )

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    with pytest.raises(UpstreamContractError):
        await adapter.create_or_update_invoice("fake_cookie", {"invoice": {}, "details": []})


@pytest.mark.asyncio
async def test_adapter_out_of_scope_stubs():
    adapter = DigitalInvoicingAdapter()
    with pytest.raises(NotImplementedError):
        await adapter.validate_invoice("cookie", "inv_123")
    with pytest.raises(NotImplementedError):
        await adapter.submit_invoice("cookie", "inv_123")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_sales_tax_rate_success():
    base_url = "https://www.digitalinvoicingsoftware.com"
    respx.get(url__startswith=f"{base_url}/api/fbr/pdi/v2/SaleTypeToRate").respond(
        status_code=200,
        json=[{"ratE_ID": 728, "ratE_DESC": "18%", "ratE_VALUE": 18}],
    )

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    rate = await adapter.fetch_sales_tax_rate("cookie", "Goods at standard rate (default)", "Punjab", "2026-08-31")
    assert rate == 18.0


@pytest.mark.asyncio
@respx.mock
async def test_fetch_sales_tax_rate_ambiguous():
    from mcp_digitalinvoice.adapter.exceptions import AmbiguousRateError

    base_url = "https://www.digitalinvoicingsoftware.com"
    respx.get(url__startswith=f"{base_url}/api/fbr/pdi/v2/SaleTypeToRate").respond(
        status_code=200,
        json=[{"ratE_VALUE": 5.0}, {"ratE_VALUE": 7.5}],
    )

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    with pytest.raises(AmbiguousRateError) as exc_info:
        await adapter.fetch_sales_tax_rate("cookie", "Electricity Supply to Retailers", "Punjab", "2026-08-31")
    assert "Multiple valid tax rates" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_sales_tax_rate_unmapped_sale_type():
    from mcp_digitalinvoice.adapter.exceptions import UnknownSaleTypeError

    adapter = DigitalInvoicingAdapter()
    with pytest.raises(UnknownSaleTypeError):
        await adapter.fetch_sales_tax_rate("cookie", "Some Unmapped Sale Type", "Punjab", "2026-08-31")


@pytest.mark.asyncio
async def test_fetch_sales_tax_rate_unmapped_province():
    from mcp_digitalinvoice.adapter.exceptions import UnknownProvinceError

    adapter = DigitalInvoicingAdapter()
    with pytest.raises(UnknownProvinceError):
        await adapter.fetch_sales_tax_rate("cookie", "Goods at standard rate (default)", "Sindh", "2026-08-31")

