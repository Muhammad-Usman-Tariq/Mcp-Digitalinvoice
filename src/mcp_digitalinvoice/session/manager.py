"""SessionManager for caching, dynamic expiry, and reactive refresh of tenant cookies."""

from datetime import datetime, timezone, timedelta
import json
import uuid
from typing import Optional, Tuple, Dict, Any
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_digitalinvoice.config import settings
from mcp_digitalinvoice.security import decrypt_secret, encrypt_secret
from mcp_digitalinvoice.models.db import TenantSession, TenantCredential, Tenant, utc_now
from mcp_digitalinvoice.adapter.client import DigitalInvoicingAdapter
from mcp_digitalinvoice.adapter.exceptions import (
    AuthenticationError,
    RateLimitError,
    ConnectionBrokenError,
)
from mcp_digitalinvoice.logging import logger


class SessionManager:
    def __init__(
        self,
        db: AsyncSession,
        redis: Optional[Redis] = None,
        adapter: Optional[DigitalInvoicingAdapter] = None,
    ):
        self.db = db
        self.redis = redis
        self.adapter = adapter or DigitalInvoicingAdapter()

    async def get_valid_cookie(self, tenant_id: uuid.UUID) -> str:
        """Retrieve a valid authentication cookie for tenant, logging in if expired or missing."""
        cookie, seller_profile = await self.get_valid_cookie_and_profile(tenant_id)
        return cookie

    async def get_valid_cookie_and_profile(
        self, tenant_id: uuid.UUID
    ) -> Tuple[str, Dict[str, Any]]:
        """Retrieve cookie and live seller company profile for tenant."""
        buffer_seconds = settings.cookie_refresh_buffer_seconds
        now = utc_now()

        # 1. Check Redis cache if available
        if self.redis:
            cache_key = f"fbr_session:tenant:{tenant_id}"
            cached_val = await self.redis.get(cache_key)
            if cached_val:
                try:
                    data = json.loads(cached_val)
                    expires_str = data.get("expires_at")
                    if expires_str:
                        expires_at = datetime.fromisoformat(expires_str)
                        if expires_at > now + timedelta(seconds=buffer_seconds):
                            return data["cookie"], data.get("profile", {})
                except Exception:
                    pass

        # 2. Check Postgres tenant_sessions
        stmt = select(TenantSession).where(TenantSession.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        db_session = res.scalar_one_or_none()

        db_expires = db_session.expires_at if db_session else None
        if db_expires and db_expires.tzinfo is None:
            db_expires = db_expires.replace(tzinfo=timezone.utc)

        if db_session and db_expires and db_expires > now + timedelta(seconds=buffer_seconds):
            decrypted_cookie = decrypt_secret(db_session.encrypted_cookie)

            # Re-populate Redis cache if available
            if self.redis:
                ttl = int((db_expires - now).total_seconds())
                if ttl > 0:
                    cache_payload = {
                        "cookie": decrypted_cookie,
                        "expires_at": db_expires.isoformat(),
                        "profile": {},
                    }
                    await self.redis.setex(
                        f"fbr_session:tenant:{tenant_id}", ttl, json.dumps(cache_payload)
                    )

            return decrypted_cookie, {}

        # 3. Cache missing or expired -> perform fresh login with rate-limit check
        if self.redis:
            rate_key = f"login_limit:tenant:{tenant_id}"
            if await self.redis.get(rate_key):
                logger.warning("Login rate limit triggered", tenant_id=str(tenant_id))
                raise RateLimitError("Login rate limit exceeded. Please wait 30 seconds before retrying.")

        # Fetch stored credentials
        cred_stmt = select(TenantCredential).where(TenantCredential.tenant_id == tenant_id)
        cred_res = await self.db.execute(cred_stmt)
        credentials = cred_res.scalar_one_or_none()

        if not credentials:
            raise ConnectionBrokenError(
                "No Digital Invoicing Software credentials found for this tenant. Please reconnect."
            )

        email = decrypt_secret(credentials.encrypted_email)
        password = decrypt_secret(credentials.encrypted_password)

        # Set rate limit flag in Redis (1 attempt per 30 seconds)
        if self.redis:
            await self.redis.setex(
                f"login_limit:tenant:{tenant_id}", settings.login_rate_limit_seconds, "1"
            )

        try:
            login_result = await self.adapter.login(email, password)
        except AuthenticationError as exc:
            logger.error("Tenant login failed - bad credentials", tenant_id=str(tenant_id))
            raise ConnectionBrokenError(
                "Authentication failed with Digital Invoicing Software. Please update tenant password."
            ) from exc

        cookie = login_result["cookie"]
        expires_at = login_result["expires_at"]
        profile = login_result.get("profile", {})

        encrypted_cookie = encrypt_secret(cookie)

        # Upsert tenant_sessions row in Postgres
        if db_session:
            db_session.encrypted_cookie = encrypted_cookie
            db_session.expires_at = expires_at
            db_session.last_refreshed_at = now
        else:
            new_session = TenantSession(
                tenant_id=tenant_id,
                encrypted_cookie=encrypted_cookie,
                expires_at=expires_at,
                last_refreshed_at=now,
            )
            self.db.add(new_session)

        await self.db.commit()

        # Cache in Redis with dynamic TTL
        if self.redis:
            ttl = int((expires_at - now).total_seconds())
            if ttl > 0:
                cache_payload = {
                    "cookie": cookie,
                    "expires_at": expires_at.isoformat(),
                    "profile": profile,
                }
                await self.redis.setex(
                    f"fbr_session:tenant:{tenant_id}", ttl, json.dumps(cache_payload)
                )

        return cookie, profile

    async def invalidate_cookie(self, tenant_id: uuid.UUID) -> None:
        """Purge cached cookie for reactive refresh when 401 occurs."""
        if self.redis:
            await self.redis.delete(f"fbr_session:tenant:{tenant_id}")

        stmt = select(TenantSession).where(TenantSession.tenant_id == tenant_id)
        res = await self.db.execute(stmt)
        db_session = res.scalar_one_or_none()
        if db_session:
            await self.db.delete(db_session)
            await self.db.commit()
