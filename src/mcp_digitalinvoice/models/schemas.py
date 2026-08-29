"""Pydantic schemas for REST API & MCP Tool inputs and outputs."""

from typing import Optional, Any, List
from pydantic import BaseModel, Field, ConfigDict


class BuyerInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    businessName: Optional[str] = Field(default=None, description="Buyer company or business name")
    ntnCnic: Optional[str] = Field(default=None, description="Buyer NTN or CNIC number")
    province: Optional[str] = Field(default=None, description="Buyer province/state")
    address: Optional[str] = Field(default=None, description="Buyer full address")
    registrationType: Optional[str] = Field(default=None, description="Buyer tax registration type")
    strn: Optional[str] = Field(default=None, description="Buyer STRN number")


class InvoiceItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    hsCode: Optional[str] = Field(default=None, description="Harmonized System code")
    description: Optional[str] = Field(default=None, description="Line item description")
    quantity: Optional[Any] = Field(default=None, description="Item quantity (must be positive number)")
    saleType: Optional[str] = Field(default=None, description="Type of sale e.g. Taxable Goods")
    uom: Optional[str] = Field(default=None, description="Unit of measurement")
    rate: Optional[Any] = Field(default=None, description="Unit rate or percentage")


class InvoiceMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    invoiceRefNo: Optional[str] = Field(default=None)
    poNumber: Optional[str] = Field(default=None)
    mivNumber: Optional[str] = Field(default=None)
    dcNumber: Optional[str] = Field(default=None)
    vendorCode: Optional[str] = Field(default=None)
    scenarioId: Optional[str] = Field(default=None)
    invoiceDate: Optional[str] = Field(default=None)


class FillInvoiceInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    buyer: Optional[BuyerInfo] = Field(default=None, description="Buyer details")
    items: Optional[List[InvoiceItem]] = Field(default=None, description="Invoice line items")
    meta: Optional[InvoiceMeta] = Field(default=None, description="Optional metadata fields")
    sourceDocumentHash: Optional[str] = Field(
        default=None, description="SHA-256 hash of source document for idempotency"
    )


class ConnectAccountInput(BaseModel):
    email: str = Field(..., description="Tenant Digital Invoicing Software email")
    password: str = Field(..., description="Tenant Digital Invoicing Software password")
    name: str = Field(..., description="Tenant business or company name")


class ConnectAccountResult(BaseModel):
    tenant_id: str
    mcp_api_key: str
    status: str = "connected"
    message: str = "Account connected successfully. Save your MCP API key."


class FillInvoiceResult(BaseModel):
    status: str  # "saved" | "needs_info" | "failed"
    remote_invoice_id: Optional[str] = None
    missing_fields: Optional[List[str]] = None
    summary: str
    error: Optional[str] = None


class GenericToolResult(BaseModel):
    status: str
    summary: str
    error: Optional[str] = None
