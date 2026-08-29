"""Tests for mapper module translating camelCase FBR extraction to snake_case payload."""

from mcp_digitalinvoice.models.schemas import (
    FillInvoiceInput,
    BuyerInfo,
    InvoiceItem,
    InvoiceMeta,
)
from mcp_digitalinvoice.adapter.mapper import map_fbr_schema_to_internal_payload


def test_mapper_conversion(synthetic_tenant_data, synthetic_buyer_data, synthetic_item_data):
    seller_profile = {
        "business_name": synthetic_tenant_data["name"],
        "ntninc": synthetic_tenant_data["ntn"],
        "province": synthetic_tenant_data["province"],
        "address": synthetic_tenant_data["address"],
    }

    input_data = FillInvoiceInput(
        buyer=BuyerInfo(**synthetic_buyer_data),
        items=[InvoiceItem(**synthetic_item_data)],
        meta=InvoiceMeta(invoiceRefNo="REF123", poNumber="PO456"),
    )

    payload = map_fbr_schema_to_internal_payload(input_data, seller_profile)

    assert "invoice" in payload
    assert "details" in payload

    inv = payload["invoice"]
    assert inv["seller_business_name"] == synthetic_tenant_data["name"]
    assert inv["seller_ntninc"] == synthetic_tenant_data["ntn"]
    assert inv["buyer_business_name"] == synthetic_buyer_data["businessName"]
    assert inv["buyer_province"] == synthetic_buyer_data["province"]
    assert inv["invoice_ref_no"] == "REF123"
    assert inv["po_number"] == "PO456"

    assert len(payload["details"]) == 1
    det = payload["details"][0]
    assert det["hscode"] == synthetic_item_data["hsCode"]
    assert det["quantity"] == float(synthetic_item_data["quantity"])
    assert det["sale_type"] == synthetic_item_data["saleType"]
