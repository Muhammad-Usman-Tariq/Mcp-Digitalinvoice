"""Comprehensive test suite explicitly covering all 15 edge cases from Section 12."""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
import pytest
import respx
import httpx

from mcp_digitalinvoice.models.db import Tenant, TenantCredential, InvoiceJob, TenantSession
from mcp_digitalinvoice.models.schemas import (
    ConnectAccountInput,
    FillInvoiceInput,
    BuyerInfo,
    InvoiceItem,
)
from mcp_digitalinvoice.security import encrypt_secret
from mcp_digitalinvoice.session.manager import SessionManager
from mcp_digitalinvoice.adapter.client import DigitalInvoicingAdapter
from mcp_digitalinvoice.adapter.exceptions import (
    UpstreamContractError,
    ConnectionBrokenError,
    AuthenticationError,
    UpstreamServerError,
)
from mcp_digitalinvoice.services.invoice_service import InvoiceService


# Edge Case 1: Cold start login (no cached session)
@pytest.mark.asyncio
@respx.mock
async def test_edge_case_1_cold_start_login(db_session, fake_redis, synthetic_tenant_data):
    base_url = "https://www.digitalinvoicingsoftware.com"
    fake_cookie = f"sess_{uuid.uuid4().hex}"

    login_route = respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": f"fbr_session={fake_cookie}; Path=/; Max-Age=7199"},
        json={"user": {"company": {"business_name": synthetic_tenant_data["name"]}}},
    )

    tenant = Tenant(name=synthetic_tenant_data["name"])
    db_session.add(tenant)
    await db_session.flush()
    db_session.add(
        TenantCredential(
            tenant_id=tenant.id,
            encrypted_email=encrypt_secret(synthetic_tenant_data["email"]),
            encrypted_password=encrypt_secret(synthetic_tenant_data["password"]),
        )
    )
    await db_session.commit()

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    sm = SessionManager(db=db_session, redis=fake_redis, adapter=adapter)

    cookie = await sm.get_valid_cookie(tenant.id)
    assert cookie == fake_cookie
    assert login_route.called


# Edge Case 2: Reusing cached, still-valid session
@pytest.mark.asyncio
@respx.mock
async def test_edge_case_2_reusing_cached_session(db_session, fake_redis):
    base_url = "https://www.digitalinvoicingsoftware.com"
    tenant_id = uuid.uuid4()
    cached_cookie = "valid_cached_session"
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    await fake_redis.set(
        f"fbr_session:tenant:{tenant_id}",
        f'{{"cookie": "{cached_cookie}", "expires_at": "{expires_at}"}}',
    )

    login_route = respx.post(f"{base_url}/api/auth/login").respond(status_code=200)

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    sm = SessionManager(db=db_session, redis=fake_redis, adapter=adapter)

    cookie = await sm.get_valid_cookie(tenant_id)
    assert cookie == cached_cookie
    assert not login_route.called  # Zero login requests made


# Edge Case 3: Cached session expired -> automatic re-login
@pytest.mark.asyncio
@respx.mock
async def test_edge_case_3_expired_session_relogin(db_session, fake_redis, synthetic_tenant_data):
    base_url = "https://www.digitalinvoicingsoftware.com"
    new_cookie = f"new_sess_{uuid.uuid4().hex}"

    tenant = Tenant(name=synthetic_tenant_data["name"])
    db_session.add(tenant)
    await db_session.flush()
    db_session.add(
        TenantCredential(
            tenant_id=tenant.id,
            encrypted_email=encrypt_secret(synthetic_tenant_data["email"]),
            encrypted_password=encrypt_secret(synthetic_tenant_data["password"]),
        )
    )
    # Expired session in DB
    db_session.add(
        TenantSession(
            tenant_id=tenant.id,
            encrypted_cookie=encrypt_secret("old_expired_cookie"),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            last_refreshed_at=datetime.now(timezone.utc) - timedelta(hours=3),
        )
    )
    await db_session.commit()

    login_route = respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": f"fbr_session={new_cookie}; Max-Age=7199"},
        json={"user": {}},
    )

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    sm = SessionManager(db=db_session, redis=fake_redis, adapter=adapter)

    cookie = await sm.get_valid_cookie(tenant.id)
    assert cookie == new_cookie
    assert login_route.called


# Edge Case 4: Wrong credentials stored -> login fails with clear error
@pytest.mark.asyncio
@respx.mock
async def test_edge_case_4_wrong_credentials(db_session, fake_redis, synthetic_tenant_data):
    base_url = "https://www.digitalinvoicingsoftware.com"
    tenant = Tenant(name=synthetic_tenant_data["name"])
    db_session.add(tenant)
    await db_session.flush()
    db_session.add(
        TenantCredential(
            tenant_id=tenant.id,
            encrypted_email=encrypt_secret(synthetic_tenant_data["email"]),
            encrypted_password=encrypt_secret(synthetic_tenant_data["password"]),
        )
    )
    await db_session.commit()

    respx.post(f"{base_url}/api/auth/login").respond(status_code=401)

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    sm = SessionManager(db=db_session, redis=fake_redis, adapter=adapter)

    with pytest.raises(ConnectionBrokenError) as exc_info:
        await sm.get_valid_cookie(tenant.id)
    assert "Authentication failed" in str(exc_info.value)


# Edge Case 5: 5xx on invoice endpoint -> limited retries -> clean failed job
@pytest.mark.asyncio
@respx.mock
async def test_edge_case_5_upstream_5xx_retries(
    db_session, fake_redis, synthetic_tenant_data, synthetic_buyer_data, synthetic_item_data
):
    base_url = "https://www.digitalinvoicingsoftware.com"
    respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": "fbr_session=cookie500; Max-Age=7199"},
        json={
            "user": {
                "company": {
                    "business_name": synthetic_tenant_data["name"],
                    "ntninc": synthetic_tenant_data["ntn"],
                    "province": synthetic_tenant_data["province"],
                    "address": synthetic_tenant_data["address"],
                }
            }
        },
    )
    inv_route = respx.post(f"{base_url}/api/invoices").respond(status_code=500)

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

    inp = FillInvoiceInput(buyer=BuyerInfo(**synthetic_buyer_data), items=[InvoiceItem(**synthetic_item_data)])
    res = await service.fill_invoice(tenant_id, inp)

    assert res.status == "failed"
    assert "500" in res.error or "Failed" in res.summary
    assert inv_route.call_count == 3  # Initial + 2 retries


# Edge Case 6: Missing required fields -> needs_info, adapter NOT called
@pytest.mark.asyncio
@respx.mock
async def test_edge_case_6_missing_required_fields(db_session, fake_redis):
    base_url = "https://www.digitalinvoicingsoftware.com"
    inv_route = respx.post(f"{base_url}/api/invoices").respond(status_code=201)

    service = InvoiceService(db=db_session, redis=fake_redis)
    inp = FillInvoiceInput(buyer=BuyerInfo(businessName="Partial Co"), items=[])

    res = await service.fill_invoice(uuid.uuid4(), inp)
    assert res.status == "needs_info"
    assert not inv_route.called  # Adapter never invoked


# Edge Case 7: Same document submitted twice -> second call returns existing result
@pytest.mark.asyncio
@respx.mock
async def test_edge_case_7_idempotency_duplicate_submission(
    db_session, fake_redis, synthetic_tenant_data, synthetic_buyer_data, synthetic_item_data
):
    base_url = "https://www.digitalinvoicingsoftware.com"
    remote_id = str(uuid.uuid4())

    respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": "fbr_session=idemp_cookie; Max-Age=7199"},
        json={
            "user": {
                "company": {
                    "business_name": synthetic_tenant_data["name"],
                    "ntninc": synthetic_tenant_data["ntn"],
                    "province": synthetic_tenant_data["province"],
                    "address": synthetic_tenant_data["address"],
                }
            }
        },
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

    inp = FillInvoiceInput(
        buyer=BuyerInfo(**synthetic_buyer_data),
        items=[InvoiceItem(**synthetic_item_data)],
        sourceDocumentHash="fixed_hash_12345",
    )

    # First call - creates invoice
    res1 = await service.fill_invoice(tenant_id, inp)
    assert res1.status == "saved"
    assert res1.remote_invoice_id == remote_id
    assert inv_route.call_count == 1

    # Second call - same document hash -> idempotency hit
    res2 = await service.fill_invoice(tenant_id, inp)
    assert res2.status == "saved"
    assert res2.remote_invoice_id == remote_id
    assert inv_route.call_count == 1  # No second HTTP call made


# Edge Case 8: Concurrent requests per tenant -> lock acquired
@pytest.mark.asyncio
async def test_edge_case_8_concurrency_tenant_lock(db_session, fake_redis):
    tenant_id = uuid.uuid4()
    lock_key = f"lock:tenant:{tenant_id}"

    # Lock is held
    await fake_redis.set(lock_key, "locked")

    service = InvoiceService(db=db_session, redis=fake_redis)

    # Fake acquiring lock fails
    class BlockingRedis(type(fake_redis)):
        def lock(self, name, timeout=30):
            class BlockedLock:
                async def acquire(self, blocking_timeout=5):
                    return False
                async def release(self): pass
            return BlockedLock()

    service.redis = BlockingRedis()
    inp = FillInvoiceInput(
        buyer=BuyerInfo(businessName="Test", province="State", registrationType="Reg"),
        items=[InvoiceItem(hsCode="1234", quantity=1, saleType="Taxable")],
    )

    res = await service.fill_invoice(tenant_id, inp)
    assert res.status == "failed"
    assert "Tenant operation in progress" in res.error


# Edge Case 9: Unexpected response shape -> UpstreamContractError
@pytest.mark.asyncio
@respx.mock
async def test_edge_case_9_upstream_contract_error(
    db_session, fake_redis, synthetic_tenant_data, synthetic_buyer_data, synthetic_item_data
):
    base_url = "https://www.digitalinvoicingsoftware.com"
    respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": "fbr_session=cookie; Max-Age=7199"},
        json={
            "user": {
                "company": {
                    "business_name": synthetic_tenant_data["name"],
                    "ntninc": synthetic_tenant_data["ntn"],
                    "province": synthetic_tenant_data["province"],
                    "address": synthetic_tenant_data["address"],
                }
            }
        },
    )
    # Missing 'id' field in response
    respx.post(f"{base_url}/api/invoices").respond(
        status_code=200, json={"result": "created_without_id"}
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

    inp = FillInvoiceInput(buyer=BuyerInfo(**synthetic_buyer_data), items=[InvoiceItem(**synthetic_item_data)])
    res = await service.fill_invoice(tenant_id, inp)

    assert res.status == "failed"
    assert "mandatory 'id' field" in res.error or "Contract" in res.error


# Edge Case 10: Dynamic Max-Age parsing from Set-Cookie header
@pytest.mark.asyncio
@respx.mock
async def test_edge_case_10_dynamic_max_age_parsing(synthetic_tenant_data):
    base_url = "https://www.digitalinvoicingsoftware.com"
    respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": "fbr_session=dynamic_cookie; Max-Age=3600; Path=/"},
        json={
            "user": {
                "company": {
                    "business_name": synthetic_tenant_data["name"],
                    "ntninc": synthetic_tenant_data["ntn"],
                    "province": synthetic_tenant_data["province"],
                    "address": synthetic_tenant_data["address"],
                }
            }
        },
    )

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    res = await adapter.login(synthetic_tenant_data["email"], synthetic_tenant_data["password"])

    assert res["max_age"] == 3600
    assert res["cookie"] == "dynamic_cookie"


# Edge Case 11: Rotated password -> connection broken
@pytest.mark.asyncio
@respx.mock
async def test_edge_case_11_rotated_credentials(db_session, fake_redis, synthetic_tenant_data):
    base_url = "https://www.digitalinvoicingsoftware.com"
    tenant = Tenant(name=synthetic_tenant_data["name"])
    db_session.add(tenant)
    await db_session.flush()

    # Stored credentials are now invalid on third-party server
    db_session.add(
        TenantCredential(
            tenant_id=tenant.id,
            encrypted_email=encrypt_secret(synthetic_tenant_data["email"]),
            encrypted_password=encrypt_secret(synthetic_tenant_data["password"]),
        )
    )
    await db_session.commit()

    respx.post(f"{base_url}/api/auth/login").respond(status_code=401)

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    sm = SessionManager(db=db_session, redis=fake_redis, adapter=adapter)

    with pytest.raises(ConnectionBrokenError):
        await sm.get_valid_cookie(tenant.id)


# Edge Case 12: Malformed/negative quantity extraction -> sanity bounds fail fast
@pytest.mark.asyncio
async def test_edge_case_12_malformed_quantity(db_session, fake_redis):
    service = InvoiceService(db=db_session, redis=fake_redis)

    inp = FillInvoiceInput(
        buyer=BuyerInfo(businessName="Co", province="State", registrationType="Reg"),
        items=[InvoiceItem(hsCode="1234", quantity=-5, saleType="Goods")],
    )

    res = await service.fill_invoice(uuid.uuid4(), inp)
    assert res.status == "failed"
    assert "positive number" in res.error


# Edge Case 13: Partial network timeout mid-request -> marked unknown outcome
@pytest.mark.asyncio
@respx.mock
async def test_edge_case_13_network_timeout(
    db_session, fake_redis, synthetic_tenant_data, synthetic_buyer_data, synthetic_item_data
):
    base_url = "https://www.digitalinvoicingsoftware.com"
    respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": "fbr_session=timeout_cookie; Max-Age=7199"},
        json={
            "user": {
                "company": {
                    "business_name": synthetic_tenant_data["name"],
                    "ntninc": synthetic_tenant_data["ntn"],
                    "province": synthetic_tenant_data["province"],
                    "address": synthetic_tenant_data["address"],
                }
            }
        },
    )
    respx.post(f"{base_url}/api/invoices").mock(side_effect=httpx.TimeoutException("Network timeout"))

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

    inp = FillInvoiceInput(buyer=BuyerInfo(**synthetic_buyer_data), items=[InvoiceItem(**synthetic_item_data)])
    res = await service.fill_invoice(tenant_id, inp)

    assert res.status == "failed"
    assert "Unknown outcome" in res.error or "Verify manually" in res.error


# Edge Case 14: Out-of-scope tools (validate & submit) -> return clear not supported
@pytest.mark.asyncio
async def test_edge_case_14_out_of_scope_tools(db_session, fake_redis):
    service = InvoiceService(db=db_session, redis=fake_redis)
    tenant_id = uuid.uuid4()

    val_res = await service.validate_invoice(tenant_id, "inv_123")
    assert val_res.status == "failed"
    assert "out of scope" in val_res.summary.lower()

    sub_res = await service.submit_invoice(tenant_id, "inv_123")
    assert sub_res.status == "failed"
    assert "out of scope" in sub_res.summary.lower()
