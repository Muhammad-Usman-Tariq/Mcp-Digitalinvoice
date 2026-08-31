"""FBR reference code tables. These are fixed government reference codes
shared by every tenant (not business/tenant data) — captured directly from
the target site's own bootstrap lookup endpoints (`provinces`,
`transtypecode`). Match against these case-insensitively and with
whitespace stripped, since source data has inconsistent casing/spacing
(e.g. profile province "Punjab" vs reference list "PUNJAB"; some
transaction descriptions have stray leading/trailing spaces)."""

from typing import Optional

PROVINCE_TO_SUPPLIER_ID: dict[str, int] = {
    "BALOCHISTAN": 2,
    "AZAD JAMMU AND KASHMIR": 4,
    "CAPITAL TERRITORY": 5,
    "KHYBER PAKHTUNKHWA": 6,
    "PUNJAB": 7,
    "SINDH": 8,
    "GILGIT BALTISTAN": 9,
}

SALE_TYPE_TO_TRANS_TYPE_ID: dict[str, int] = {
    "GOODS AT STANDARD RATE (DEFAULT)": 75,
    "GOODS AT REDUCED RATE": 24,
    "GOODS AT ZERO-RATE": 80,
    "PETROLEUM PRODUCTS": 85,
    "ELECTRICITY SUPPLY TO RETAILERS": 62,
    "SIM": 129,
    "GAS TO CNG STATIONS": 77,
    "MOBILE PHONES": 122,
    "PROCESSING/CONVERSION OF GOODS": 25,
    "3RD SCHEDULE GOODS": 23,
    "GOODS (FED IN ST MODE)": 21,
    "SERVICES (FED IN ST MODE)": 22,
    "SERVICES": 18,
    "EXEMPT GOODS": 81,
    "DTRE GOODS": 82,
    "COTTON GINNERS": 130,
    "ELECTRIC VEHICLE": 132,
    "CEMENT /CONCRETE BLOCK": 134,
    "TELECOMMUNICATION SERVICES": 84,
    "STEEL MELTING AND RE-ROLLING": 123,
    "SHIP BREAKING": 125,
    "POTASSIUM CHLORATE": 115,
    "CNG SALES": 178,
    "TOLL MANUFACTURING": 181,
    "NON-ADJUSTABLE SUPPLIES": 138,
    "GOODS AS PER SRO.297(|)/2023": 139,
}


def normalize_lookup_key(raw: str) -> str:
    """Uppercase + collapse/strip whitespace for reliable matching against
    the tables above, since source data has inconsistent casing/spacing."""
    if not raw:
        return ""
    return " ".join(raw.strip().upper().split())


def lookup_province_code(province_name: str) -> Optional[int]:
    return PROVINCE_TO_SUPPLIER_ID.get(normalize_lookup_key(province_name))


def lookup_trans_type_id(sale_type_name: str) -> Optional[int]:
    return SALE_TYPE_TO_TRANS_TYPE_ID.get(normalize_lookup_key(sale_type_name))
