"""Invoice service orchestrating validation, idempotency, locks, and adapter execution."""

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_digitalinvoice.config import settings
from mcp_digitalinvoice.security import (
    encrypt_secret,
    generate_mcp_api_key,
    hash_api_key,
)
from mcp_digitalinvoice.models.db import (
    Tenant,
    TenantCredential,
    MCPAPIKey,
    InvoiceJob,
    utc_now,
)
from mcp_digitalinvoice.models.schemas import (
    ConnectAccountInput,
    ConnectAccountResult,
    FillInvoiceInput,
    FillInvoiceResult,
    GenericToolResult,
)
from mcp_digitalinvoice.session.manager import SessionManager
from mcp_digitalinvoice.adapter.client import DigitalInvoicingAdapter
from mcp_digitalinvoice.adapter.mapper import map_fbr_schema_to_internal_payload
from mcp_digitalinvoice.adapter.exceptions import (
    UpstreamContractError,
    AuthenticationError,
    UpstreamServerError,
    AdapterError,
    ConnectionBrokenError,
    MissingSellerProfileError,
    AmbiguousRateError,
    UnknownSaleTypeError,
    UnknownProvinceError,
)
from mcp_digitalinvoice.logging import logger


class InvoiceService:
    def __init__(
        self,
        db: AsyncSession,
        redis: Optional[Redis] = None,
        adapter: Optional[DigitalInvoicingAdapter] = None,
    ):
        self.db = db
        self.redis = redis
        self.adapter = adapter or DigitalInvoicingAdapter()
        self.session_manager = SessionManager(db, redis, self.adapter)

    async def connect_account(self, input_data: ConnectAccountInput) -> ConnectAccountResult:
        """Connect a new tenant account, validate credentials with test login, and issue an API key."""
        # 1. Test login with third-party service first
        login_res = await self.adapter.login(input_data.email, input_data.password)

        # 2. Create Tenant record
        tenant = Tenant(name=input_data.name)
        self.db.add(tenant)
        await self.db.flush()

        # 3. Store encrypted credentials
        encrypted_email = encrypt_secret(input_data.email)
        encrypted_pass = encrypt_secret(input_data.password)

        credential = TenantCredential(
            tenant_id=tenant.id,
            encrypted_email=encrypted_email,
            encrypted_password=encrypted_pass,
        )
        self.db.add(credential)

        # 4. Generate and store MCP API key
        raw_key = generate_mcp_api_key()
        hashed = hash_api_key(raw_key)

        api_key_record = MCPAPIKey(
            tenant_id=tenant.id,
            hashed_key=hashed,
        )
        self.db.add(api_key_record)

        await self.db.commit()

        logger.info("Successfully connected tenant account", tenant_id=str(tenant.id))

        return ConnectAccountResult(
            tenant_id=str(tenant.id),
            mcp_api_key=raw_key,
            status="connected",
            message="Account connected successfully. Store your MCP API key securely.",
        )

    def _validate_fill_input(self, input_data: FillInvoiceInput) -> List[str]:
        """Validate required fields in buyer and items."""
        missing = []
        buyer = input_data.buyer
        if not buyer:
            missing.extend(["buyer.businessName", "buyer.province", "buyer.registrationType"])
        else:
            if not buyer.businessName:
                missing.append("buyer.businessName")
            if not buyer.province:
                missing.append("buyer.province")
            if not buyer.registrationType:
                missing.append("buyer.registrationType")
            if buyer.registrationType == "Registered" and not buyer.ntnCnic:
                missing.append("buyer.ntnCnic")

        items = input_data.items
        if not items:
            missing.append("items (at least one item required)")
        else:
            for idx, item in enumerate(items):
                if not item.hsCode:
                    missing.append(f"items[{idx}].hsCode")
                if item.quantity is None:
                    missing.append(f"items[{idx}].quantity")
                if item.fixedValue is None:
                    missing.append(f"items[{idx}].fixedValue")
                if not item.saleType:
                    missing.append(f"items[{idx}].saleType")

        return missing

    def _check_sanity_bounds(self, input_data: FillInvoiceInput) -> Optional[str]:
        """Verify numeric bounds for item quantities, rates, and fixed values."""
        if not input_data.items:
            return None
        for idx, item in enumerate(input_data.items):
            if item.quantity is not None:
                try:
                    qty = float(item.quantity)
                    if qty <= 0:
                        return f"Item {idx} quantity must be a positive number, got {qty}."
                except (ValueError, TypeError):
                    return f"Item {idx} quantity is not a valid number."
            if item.fixedValue is not None:
                try:
                    fv = float(item.fixedValue)
                    if fv <= 0:
                        return f"Item {idx} fixedValue must be a positive number, got {fv}."
                except (ValueError, TypeError):
                    return f"Item {idx} fixedValue is not a valid number."
        return None

    async def fill_invoice(
        self, tenant_id: uuid.UUID, input_data: FillInvoiceInput
    ) -> FillInvoiceResult:
        """Process document extraction, validate fields, check idempotency, and save draft invoice."""
        # Step 1: Validate required fields
        missing_fields = self._validate_fill_input(input_data)
        if missing_fields:
            logger.info("Fill invoice validation failed", tenant_id=str(tenant_id), missing=missing_fields)
            return FillInvoiceResult(
                status="needs_info",
                missing_fields=missing_fields,
                summary=f"Missing required fields: {', '.join(missing_fields)}",
            )

        # Step 2: Sanity bounds check
        sanity_error = self._check_sanity_bounds(input_data)
        if sanity_error:
            logger.warning("Sanity bounds check failed", tenant_id=str(tenant_id), error=sanity_error)
            return FillInvoiceResult(
                status="failed",
                error=sanity_error,
                summary="Input extraction sanity bounds check failed.",
            )

        # Step 3: Compute document hash for idempotency
        if input_data.sourceDocumentHash:
            doc_hash = input_data.sourceDocumentHash
        else:
            payload_str = json.dumps(input_data.model_dump(), sort_keys=True)
            doc_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        existing_job_res = await self.db.execute(
            select(InvoiceJob)
            .where(
                InvoiceJob.tenant_id == tenant_id,
                InvoiceJob.source_document_hash == doc_hash,
            )
            .order_by(InvoiceJob.created_at.desc())
        )
        existing_job = existing_job_res.scalars().first()

        if existing_job and existing_job.status == "saved" and existing_job.remote_invoice_id:
            logger.info("Idempotent hit - returning existing saved invoice", tenant_id=str(tenant_id))
            return FillInvoiceResult(
                status="saved",
                remote_invoice_id=existing_job.remote_invoice_id,
                summary="Invoice already saved for this source document.",
            )

        # Step 4: Per-Tenant Distributed Lock
        lock = None
        lock_key = f"lock:tenant:{tenant_id}"
        if self.redis:
            try:
                lock = self.redis.lock(lock_key, timeout=30)
                acquired = await lock.acquire(blocking_timeout=5)
                if not acquired:
                    return FillInvoiceResult(
                        status="failed",
                        error="Tenant operation in progress. Concurrent call locked.",
                        summary="Another invoice is currently being processed for this tenant. Please wait.",
                    )
            except Exception as exc:
                logger.warning("Redis lock unavailable, proceeding unlocked", error=str(exc))
                lock = None

        try:
            # Create pending job record
            job = InvoiceJob(
                tenant_id=tenant_id,
                source_document_hash=doc_hash,
                extracted_payload=input_data.model_dump(),
                status="pending",
            )
            self.db.add(job)
            await self.db.flush()

            # Step 5: Resolve session & cookie
            try:
                cookie, seller_profile = await self.session_manager.get_valid_cookie_and_profile(tenant_id)
            except ConnectionBrokenError as exc:
                job.status = "failed"
                job.error_detail = str(exc)
                await self.db.commit()
                return FillInvoiceResult(
                    status="failed",
                    error=str(exc),
                    summary="Tenant connection broken. Re-authentication required via connect_account.",
                )

            # Auto-fetch tax rates for items missing explicit rate
            seller_prov = seller_profile.get("province") or seller_profile.get("seller_province") or ""
            inv_date = input_data.meta.invoiceDate if input_data.meta else None

            for idx, item in enumerate(input_data.items or []):
                if item.rate is None or item.rate == "":
                    try:
                        fetched_rate = await self.adapter.fetch_sales_tax_rate(
                            cookie, item.saleType, seller_prov, inv_date
                        )
                        item.rate = fetched_rate
                    except AmbiguousRateError as exc:
                        job.status = "needs_info"
                        job.error_detail = str(exc)
                        job.completed_at = utc_now()
                        await self.db.commit()
                        return FillInvoiceResult(
                            status="needs_info",
                            missing_fields=[f"items[{idx}].rate"],
                            summary=str(exc),
                        )
                    except (UnknownSaleTypeError, UnknownProvinceError) as exc:
                        job.status = "failed"
                        job.error_detail = str(exc)
                        job.completed_at = utc_now()
                        await self.db.commit()
                        return FillInvoiceResult(
                            status="failed",
                            summary="Could not determine tax rate automatically.",
                            error=str(exc),
                        )
                    except AdapterError as exc:
                        # Covers UpstreamServerError (timeouts/5xx), AuthenticationError,
                        # UpstreamContractError, etc. from the rate-lookup call. Without this,
                        # these exceptions were uncaught here and crashed the ASGI app with a
                        # raw 500 instead of a clean JSON "failed" result.
                        job.status = "failed"
                        job.error_detail = str(exc)
                        job.completed_at = utc_now()
                        await self.db.commit()
                        return FillInvoiceResult(
                            status="failed",
                            summary="Failed to fetch tax rate from Digital Invoicing Software (upstream/network issue). Please retry.",
                            error=str(exc),
                        )

            try:
                internal_payload = map_fbr_schema_to_internal_payload(input_data, seller_profile)
            except MissingSellerProfileError as exc:
                job.status = "failed"
                job.error_detail = str(exc)
                job.completed_at = utc_now()
                await self.db.commit()
                return FillInvoiceResult(
                    status="failed",
                    error=str(exc),
                    summary="Could not resolve seller company profile for this tenant — session data may be incomplete, try again.",
                )

            # Step 6: Call Adapter with retries and reactive refresh
            max_attempts = settings.max_retries + 1
            remote_res = None
            last_error = None
            is_timeout_error = False

            for attempt in range(max_attempts):
                try:
                    remote_res = await self.adapter.create_or_update_invoice(cookie, internal_payload)
                    break
                except AuthenticationError:
                    # Reactive cookie refresh on 401
                    logger.info("Got 401 on save invoice, invalidating cookie and retrying", attempt=attempt)
                    await self.session_manager.invalidate_cookie(tenant_id)
                    try:
                        cookie, seller_profile = await self.session_manager.get_valid_cookie_and_profile(tenant_id)
                        internal_payload = map_fbr_schema_to_internal_payload(input_data, seller_profile)
                        remote_res = await self.adapter.create_or_update_invoice(cookie, internal_payload)
                        break
                    except Exception as exc:
                        last_error = str(exc)
                        break
                except UpstreamServerError as exc:
                    last_error = str(exc)
                    if "timeout" in str(exc).lower() or "unknown" in str(exc).lower():
                        is_timeout_error = True
                    logger.warning("Upstream 5xx on invoice save attempt", attempt=attempt, error=str(exc))
                except UpstreamContractError as exc:
                    last_error = str(exc)
                    break  # Schema contract mismatch - do not retry
                except AdapterError as exc:
                    last_error = str(exc)
                    if "Timeout" in str(exc) or "unknown" in str(exc).lower():
                        is_timeout_error = True
                    break

            if remote_res and "id" in remote_res:
                remote_id = str(remote_res["id"])
                job.status = "saved"
                job.remote_invoice_id = remote_id
                job.completed_at = utc_now()
                await self.db.commit()

                return FillInvoiceResult(
                    status="saved",
                    remote_invoice_id=remote_id,
                    summary=f"Invoice draft created successfully with remote ID {remote_id}.",
                )
            else:
                job.status = "failed"
                if is_timeout_error:
                    job.error_detail = "unknown — verify manually (request timed out)"
                    err_msg = "Unknown outcome — network timeout while saving invoice. Verify manually before retrying."
                else:
                    job.error_detail = last_error or "Failed to create invoice on third-party service."
                    err_msg = job.error_detail

                job.completed_at = utc_now()
                await self.db.commit()

                return FillInvoiceResult(
                    status="failed",
                    error=err_msg,
                    summary="Failed to save draft invoice on target site.",
                )

        finally:
            if lock and self.redis:
                try:
                    await lock.release()
                except Exception:
                    pass

    async def validate_invoice(self, tenant_id: uuid.UUID, invoice_id: str) -> GenericToolResult:
        """Validate invoice stub."""
        return GenericToolResult(
            status="failed",
            summary="Validate Invoice is currently out of scope and not supported due to upstream site bugs.",
            error="Feature out of scope.",
        )

    async def submit_invoice(self, tenant_id: uuid.UUID, invoice_id: str) -> GenericToolResult:
        """Submit invoice stub."""
        return GenericToolResult(
            status="failed",
            summary="Submit Invoice is currently out of scope.",
            error="Feature out of scope.",
        )
