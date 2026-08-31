"""Tests for mapper module translating camelCase FBR extraction to snake_case payload."""

import pytest
from mcp_digitalinvoice.models.schemas import (
    FillInvoiceInput,
    BuyerInfo,
    InvoiceItem,
    InvoiceMeta,
)
from mcp_digitalinvoice.adapter.mapper import (
    map_fbr_schema_to_internal_payload,
    _parse_rate_percent,
    _parse_number,
)
from mcp_digitalinvoice.adapter.exceptions import MissingSellerProfileError


def test_parse_rate_percent():
    assert _parse_rate_percent("18%") == 18.0
    assert _parse_rate_percent("18") == 18.0
    assert _parse_rate_percent(18) == 18.0
    assert _parse_rate_percent(18.0) == 18.0
    assert _parse_rate_percent(None) == 0.0
    assert _parse_rate_percent("invalid") == 0.0


def test_parse_number():
    assert _parse_number(25) == 25.0
    assert _parse_number("78") == 78.0
    assert _parse_number(None) == 0.0
    assert _parse_number("abc") == 0.0


def test_mapper_real_world_calculations(synthetic_tenant_data, synthetic_buyer_data):
    seller_profile = {
        "business_name": synthetic_tenant_data["name"],
        "ntninc": synthetic_tenant_data["ntn"],
        "province": synthetic_tenant_data["province"],
        "address": synthetic_tenant_data["address"],
    }

    # Verified real-world numbers: qty=25, fixedValue=78, rate="18%"
    item = InvoiceItem(
        hsCode="1234.56",
        description="Widget",
        quantity=25,
        fixedValue=78,
        saleType="Taxable Goods",
        rate="18%",
    )

    input_data = FillInvoiceInput(
        buyer=BuyerInfo(**synthetic_buyer_data),
        items=[item],
        meta=InvoiceMeta(invoiceRefNo="REF123"),
    )

    payload = map_fbr_schema_to_internal_payload(input_data, seller_profile)

    assert len(payload["details"]) == 1
    det = payload["details"][0]

    assert det["product_description"] == "Widget"
    assert det["rate"] == 18.0
    assert det["fixed_invoice_value_on_retail_price"] == 78.0
    assert det["value_sales_excluding_st"] == 1950.0  # 25 * 78
    assert det["sales_tax_applicable"] == 351.0       # 1950 * 0.18
    assert det["total_value"] == 2301.0               # 1950 + 351


def test_mapper_missing_seller_profile_raises():
    input_data = FillInvoiceInput(
        buyer=BuyerInfo(businessName="Buyer Co", province="State", registrationType="Unregistered"),
        items=[InvoiceItem(hsCode="1234.56", quantity=1, fixedValue=100, saleType="Goods")],
    )

    # Empty seller profile
    with pytest.raises(MissingSellerProfileError) as exc_info:
        map_fbr_schema_to_internal_payload(input_data, {})
    assert "seller company profile" in str(exc_info.value).lower() or "missing" in str(exc_info.value).lower()

    # Incomplete seller profile
    with pytest.raises(MissingSellerProfileError):
        map_fbr_schema_to_internal_payload(input_data, {"business_name": "Seller Inc", "province": "State"})
