"""Pure mapping module between camelCase FBR extraction schemas and third-party snake_case payloads."""

from datetime import datetime, timezone
from typing import Dict, Any
from mcp_digitalinvoice.models.schemas import FillInvoiceInput, BuyerInfo, InvoiceMeta
from mcp_digitalinvoice.adapter.exceptions import MissingSellerProfileError

# TODO: In future, if description or uom are omitted by the caller, auto-fill them by calling the target site's HS_UOM lookup endpoint for the selected hsCode.


def _parse_rate_percent(raw_rate: Any) -> float:
    """Accepts '18%', '18', 18, 18.0, or None and returns a plain float like 18.0."""
    if raw_rate is None:
        return 0.0
    if isinstance(raw_rate, (int, float)):
        return float(raw_rate)
    cleaned = str(raw_rate).strip().rstrip("%").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_number(raw: Any) -> float:
    """Safely convert raw number input to float, returning 0.0 on failure/None."""
    if raw is None:
        return 0.0
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.0


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
     seller_profile.get("ntn_cnic")      # <- ye line abhi bhi hai ya gayab ho gayi?
     or seller_profile.get("ntninc")
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
    company_id = seller_profile.get("company_id")
    user_id = seller_profile.get("user_id")

    if not seller_name or not seller_ntn or not seller_province or not seller_address or not company_id or not user_id:
        missing = []
        if not seller_name:
            missing.append("business_name")
        if not seller_ntn:
            missing.append("ntninc")
        if not seller_province:
            missing.append("province")
        if not seller_address:
            missing.append("address")
        if not company_id:
            missing.append("company_id")
        if not user_id:
            missing.append("user_id")
        raise MissingSellerProfileError(
            f"Could not resolve seller company profile for this tenant — missing fields: {', '.join(missing)}."
        )

    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    invoice_data = {
        "company_id": company_id,
        "user_id": user_id,
        "seller_business_name": seller_name,
        "seller_ntninc": seller_ntn,
        "seller_province": seller_province,
        "seller_address": seller_address,
        "buyer_ntninc": buyer.ntnCnic or "",
        "buyer_business_name": buyer.businessName or "",
        "buyer_province": (buyer.province or "").strip().upper(),
        "buyer_address": buyer.address or "",
        "buyer_registration_type": buyer.registrationType or "",
        "buyer_strn": buyer.strn or "",
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
        qty = _parse_number(item.quantity)
        fixed_value = _parse_number(item.fixedValue)
        rate_pct = _parse_rate_percent(item.rate)

        value_excl_st = round(qty * fixed_value, 2)
        sales_tax = round(value_excl_st * (rate_pct / 100), 2)
        total_value = round(value_excl_st + sales_tax, 2)

        details_data.append(
            {
                "hscode": item.hsCode or "",
                "product_description": item.description or "",
                "quantity": qty,
                "sale_type": item.saleType or "",
                "uom": item.uom or "",
                "rate": rate_pct,
                "fixed_invoice_value_on_retail_price": fixed_value,
                "value_sales_excluding_st": value_excl_st,
                "sales_tax_applicable": sales_tax,
                "total_value": total_value,
                "extra_tax": 0,
                "discount": None,
                "fed_payable": None,
                "further_tax": None,
                "sales_tax_withheld_at_source": None,
                "sr_no_item_serial_no": "",
                "sr_no_schedule_no": "",
            }
        )

    # Confirmed via live DevTools capture of the site's own UI-generated request:
    # the invoice header carries an explicit "status": "draft" and a "total_amount"
    # equal to the sum of the line items' total_value. Both were previously absent
    # from our payload entirely.
    invoice_data["status"] = "draft"
    invoice_data["total_amount"] = round(sum(d["total_value"] for d in details_data), 2)

    return {"invoice": invoice_data, "details": details_data}
