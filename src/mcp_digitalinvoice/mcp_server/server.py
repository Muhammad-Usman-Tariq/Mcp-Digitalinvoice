"""Native MCP Server transport exposing tools via stdio / Streamable HTTP transport."""

import asyncio
from typing import Dict, Any, Optional, List
from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from mcp_digitalinvoice.database import AsyncSessionLocal, get_redis_client
from mcp_digitalinvoice.security import hash_api_key
from mcp_digitalinvoice.models.db import MCPAPIKey
from mcp_digitalinvoice.models.schemas import (
    ConnectAccountInput,
    FillInvoiceInput,
    BuyerInfo,
    InvoiceItem,
    InvoiceMeta,
)
from mcp_digitalinvoice.services.invoice_service import InvoiceService
from mcp_digitalinvoice.logging import configure_logging, logger

# Initialize FastMCP Server
mcp = FastMCP("Digital Invoice Autofill MCP Server")


async def _resolve_tenant_id(raw_key: str, db) -> Any:
    """Resolve tenant ID from hashed raw API key."""
    if not raw_key:
        raise ValueError("Missing mcp_api_key for tool authorization.")

    hashed = hash_api_key(raw_key)
    stmt = select(MCPAPIKey).where(
        MCPAPIKey.hashed_key == hashed, MCPAPIKey.revoked_at.is_(None)
    )
    res = await db.execute(stmt)
    key_record = res.scalar_one_or_none()

    if not key_record:
        raise ValueError("Invalid or revoked mcp_api_key.")

    return key_record.tenant_id


@mcp.tool()
async def connect_account(email: str, password: str, name: str) -> Dict[str, Any]:
    """Onboarding tool to connect a tenant's Digital Invoicing Software account.

    Stores credentials securely and issues an MCP API key required for autofilling invoices.
    """
    async with AsyncSessionLocal() as db:
        redis = get_redis_client()
        service = InvoiceService(db=db, redis=redis)
        try:
            input_data = ConnectAccountInput(email=email, password=password, name=name)
            res = await service.connect_account(input_data)
            return res.model_dump()
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}
        finally:
            if redis:
                await redis.aclose()


@mcp.tool()
async def fill_invoice(
    mcp_api_key: str,
    buyer: Dict[str, Any],
    items: List[Dict[str, Any]],
    meta: Optional[Dict[str, Any]] = None,
    source_document_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """Autofill and save a draft invoice on Digital Invoicing Software.

    CRITICAL SEQUENCING RULE FOR LLMs:
    Only process ONE document per call. If you have multiple receipts or documents,
    you MUST fully complete one fill_invoice call (and receive its result) before
    extracting data from or calling this tool for the next document.
    """
    async with AsyncSessionLocal() as db:
        redis = get_redis_client()
        try:
            tenant_id = await _resolve_tenant_id(mcp_api_key, db)
            service = InvoiceService(db=db, redis=redis)

            buyer_obj = BuyerInfo(**buyer) if buyer else None
            items_objs = [InvoiceItem(**it) for it in items] if items else []
            meta_obj = InvoiceMeta(**meta) if meta else None

            input_data = FillInvoiceInput(
                buyer=buyer_obj,
                items=items_objs,
                meta=meta_obj,
                sourceDocumentHash=source_document_hash,
            )

            res = await service.fill_invoice(tenant_id, input_data)
            return res.model_dump()
        except Exception as exc:
            logger.error("Error in fill_invoice MCP tool", error=str(exc))
            return {"status": "failed", "error": str(exc), "summary": "MCP tool execution failed."}
        finally:
            if redis:
                await redis.aclose()


@mcp.tool()
async def validate_invoice(mcp_api_key: str, invoice_id: str) -> Dict[str, Any]:
    """Validate an invoice against tax authority rules (Out of scope / Currently not supported)."""
    async with AsyncSessionLocal() as db:
        redis = get_redis_client()
        try:
            tenant_id = await _resolve_tenant_id(mcp_api_key, db)
            service = InvoiceService(db=db, redis=redis)
            res = await service.validate_invoice(tenant_id, invoice_id)
            return res.model_dump()
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}
        finally:
            await redis.aclose()


@mcp.tool()
async def submit_invoice(mcp_api_key: str, invoice_id: str) -> Dict[str, Any]:
    """Submit a validated invoice (Out of scope / Currently not supported)."""
    async with AsyncSessionLocal() as db:
        redis = get_redis_client()
        try:
            tenant_id = await _resolve_tenant_id(mcp_api_key, db)
            service = InvoiceService(db=db, redis=redis)
            res = await service.submit_invoice(tenant_id, invoice_id)
            return res.model_dump()
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}
        finally:
            await redis.aclose()


def main():
    """Run the MCP server stdio transport."""
    configure_logging()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
