"""Tests for session manager caching, dynamic expiry, and reactive refresh."""

import uuid
from datetime import datetime, timezone, timedelta
import pytest
import respx

from mcp_digitalinvoice.models.db import Tenant, TenantCredential
from mcp_digitalinvoice.security import encrypt_secret
from mcp_digitalinvoice.session.manager import SessionManager
from mcp_digitalinvoice.adapter.client import DigitalInvoicingAdapter
from mcp_digitalinvoice.adapter.exceptions import RateLimitError, ConnectionBrokenError


@pytest.mark.asyncio
@respx.mock
async def test_session_manager_cold_start_login(
    db_session, fake_redis, synthetic_tenant_data
):
    base_url = "https://www.digitalinvoicingsoftware.com"
    fake_cookie = f"sess_{uuid.uuid4().hex}"

    respx.post(f"{base_url}/api/auth/login").respond(
        status_code=200,
        headers={"Set-Cookie": f"fbr_session={fake_cookie}; Path=/; Max-Age=7199"},
        json={"user": {"company": {"business_name": synthetic_tenant_data["name"]}}},
    )

    tenant = Tenant(name=synthetic_tenant_data["name"])
    db_session.add(tenant)
    await db_session.flush()

    cred = TenantCredential(
        tenant_id=tenant.id,
        encrypted_email=encrypt_secret(synthetic_tenant_data["email"]),
        encrypted_password=encrypt_secret(synthetic_tenant_data["password"]),
    )
    db_session.add(cred)
    await db_session.commit()

    adapter = DigitalInvoicingAdapter(base_url=base_url)
    sm = SessionManager(db=db_session, redis=fake_redis, adapter=adapter)

    cookie = await sm.get_valid_cookie(tenant.id)
    assert cookie == fake_cookie


@pytest.mark.asyncio
async def test_session_manager_cached_cookie(db_session, fake_redis):
    tenant_id = uuid.uuid4()
    fake_cookie = "cached_cookie_val"
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    # Pre-populate Redis cache
    await fake_redis.set(
        f"fbr_session:tenant:{tenant_id}",
        f'{{"cookie": "{fake_cookie}", "expires_at": "{expires_at}"}}',
    )

    sm = SessionManager(db=db_session, redis=fake_redis)
    cookie = await sm.get_valid_cookie(tenant_id)
    assert cookie == fake_cookie


@pytest.mark.asyncio
async def test_session_manager_rate_limit(db_session, fake_redis):
    tenant_id = uuid.uuid4()
    await fake_redis.setex(f"login_limit:tenant:{tenant_id}", 30, "1")

    sm = SessionManager(db=db_session, redis=fake_redis)
    with pytest.raises(RateLimitError):
        await sm.get_valid_cookie(tenant_id)
