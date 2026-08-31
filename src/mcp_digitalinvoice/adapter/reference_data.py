"""FBR reference code tables.

These are fixed government codes shared by all tenants (not business data) —
extend as more are discovered via live inspection of the target site's own
SaleTypeToRate calls, following the same process used to build this initial set.
Never guess a code.
"""

SALE_TYPE_TO_TRANS_TYPE_ID: dict[str, int] = {
    "Goods at standard rate (default)": 75,
    "Electricity Supply to Retailers": 62,
}

PROVINCE_TO_SUPPLIER_ID: dict[str, int] = {
    "Punjab": 7,
}
