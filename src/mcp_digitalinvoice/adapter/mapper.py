"""Pure mapping module between camelCase FBR extraction schemas and third-party snake_case payloads."""

from datetime import datetime, timezone
from typing import Dict, Any
from mcp_digitalinvoice.models.schemas import FillInvoiceInput, BuyerInfo, InvoiceMeta
from mcp_digitalinvoice.adapter.exceptions import MissingSellerProfileError


def map_fbr_schema_to_internal_payload(
    input_data: FillInvoiceInput, seller_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """Map external extraction payload and live seller profile to Digital Invoicing Software payload."""
    buyer = input_data.buyer or BuyerInfo()
    meta = input_data.meta or InvoiceMeta()
    items = input_data.items or []

    if not seller_profile or not isinstance(seller_profile, dict):
        raise MissingSellerProfileError("Seller profile data is missing or invalid.")

    # Seller identity is ALWAYS sourced from tenant live login profile, never hardcoded
    seller_name = (
        seller_profile.get("business_name")
        or seller_profile.get("seller_business_name")
        or seller_profile.get("company_name")
        or seller_profile.get("name")
    )
    seller_ntn = (
        seller_profile.get("ntninc")
        or seller_profile.get("seller_ntninc")
        or seller_profile.get("ntn")
    )
    seller_province = (
        seller_profile.get("province")
        or seller_profile.get("seller_province")
        or seller_profile.get("state")
    )
    seller_address = (
        seller_profile.get("address")
        or seller_profile.get("seller_address")
    )

    if not seller_name or not seller_ntn or not seller_province or not seller_address:
        missing = []
        if not seller_name:
            missing.append("business_name")
        if not seller_ntn:
            missing.append("ntninc")
        if not seller_province:
            missing.append("province")
        if not seller_address:
            missing.append("address")
        raise MissingSellerProfileError(
            f"Could not resolve seller company profile for this tenant — missing fields: {', '.join(missing)}."
        )

    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    invoice_data = {
        "seller_business_name": seller_name,
        "seller_ntninc": seller_ntn,
        "seller_province": seller_province,
        "seller_address": seller_address,
        "buyer_ntninc": buyer.ntnCnic or "",
        "buyer_business_name": buyer.businessName or "",
        "buyer_province": buyer.province or "",
        "buyer_address": buyer.address or "",
        "buyer_registration_type": buyer.registrationType or "",
        "invoice_type": "Sale Invoice",
        "invoice_date": meta.invoiceDate or current_date,
        "invoice_ref_no": meta.invoiceRefNo or "",
        "po_number": meta.poNumber or "",
        "miv_number": meta.mivNumber or "",
        "dc_number": meta.dcNumber or "",
        "vendor_code": meta.vendorCode or "",
        "scenario_id": meta.scenarioId or "",
    }

    details_data = []
    for item in items:
        qty = 0.0
        if item.quantity is not None:
            try:
                qty = float(item.quantity)
            except (ValueError, TypeError):
                qty = 0.0

        details_data.append(
            {
                "invoice_id": "",
                "hscode": item.hsCode or "",
                "description": item.description or "",
                "quantity": qty,
                "sale_type": item.saleType or "",
                "uom": item.uom or "",
                "rate": str(item.rate) if item.rate is not None else "",
            }
        )

    return {"invoice": invoice_data, "details": details_data}
