"""FastAPI REST routes exposing tools via OpenAPI function calling."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from mcp_digitalinvoice.database import get_db_session, get_redis_client
from mcp_digitalinvoice.security import hash_api_key
from mcp_digitalinvoice.models.db import MCPAPIKey
from mcp_digitalinvoice.models.schemas import (
    ConnectAccountInput,
    ConnectAccountResult,
    FillInvoiceInput,
    FillInvoiceResult,
    GenericToolResult,
)
from mcp_digitalinvoice.services.invoice_service import InvoiceService
from mcp_digitalinvoice.adapter.exceptions import AdapterError

router = APIRouter(prefix="/api/v1", tags=["Invoice Autofill Tools"])
security_scheme = HTTPBearer(auto_error=False)


async def get_current_tenant_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db_session),
) -> uuid.UUID:
    """Resolve tenant ID from Bearer token or X-API-Key header."""
    raw_key = None
    if credentials and credentials.credentials:
        raw_key = credentials.credentials
    elif x_api_key:
        raw_key = x_api_key

    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing MCP API Key in Authorization Bearer header or X-API-Key header.",
        )

    hashed = hash_api_key(raw_key)
    stmt = select(MCPAPIKey).where(
        MCPAPIKey.hashed_key == hashed, MCPAPIKey.revoked_at.is_(None)
    )
    res = await db.execute(stmt)
    key_record = res.scalar_one_or_none()

    if not key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked MCP API Key.",
        )

    return key_record.tenant_id


@router.post("/connect_account", response_model=ConnectAccountResult)
async def connect_account_endpoint(
    body: ConnectAccountInput,
    db: AsyncSession = Depends(get_db_session),
    redis: Optional[Redis] = Depends(get_redis_client),
):
    """Onboarding endpoint to register tenant Digital Invoicing Software credentials and issue API Key."""
    service = InvoiceService(db=db, redis=redis)
    try:
        return await service.connect_account(body)
    except AdapterError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect account: {str(exc)}",
        )
    finally:
        if redis:
            await redis.aclose()


@router.post("/fill_invoice", response_model=FillInvoiceResult)
async def fill_invoice_endpoint(
    body: FillInvoiceInput,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
    redis: Optional[Redis] = Depends(get_redis_client),
):
    """Autofill and save draft invoice on Digital Invoicing Software."""
    service = InvoiceService(db=db, redis=redis)
    try:
        return await service.fill_invoice(tenant_id, body)
    finally:
        if redis:
            await redis.aclose()


@router.post("/validate_invoice", response_model=GenericToolResult)
async def validate_invoice_endpoint(
    invoice_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
    redis: Optional[Redis] = Depends(get_redis_client),
):
    """Validation stub (Out of scope)."""
    service = InvoiceService(db=db, redis=redis)
    try:
        return await service.validate_invoice(tenant_id, invoice_id)
    finally:
        if redis:
            await redis.aclose()


@router.post("/submit_invoice", response_model=GenericToolResult)
async def submit_invoice_endpoint(
    invoice_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db_session),
    redis: Optional[Redis] = Depends(get_redis_client),
):
    """Submit invoice stub (Out of scope)."""
    service = InvoiceService(db=db, redis=redis)
    try:
        return await service.submit_invoice(tenant_id, invoice_id)
    finally:
        if redis:
            await redis.aclose()
