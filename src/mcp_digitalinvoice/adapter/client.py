"""Async HTTP client adapter for talking to Digital Invoicing Software API."""

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import httpx
from mcp_digitalinvoice.config import settings
from mcp_digitalinvoice.adapter.reference_data import (
    lookup_province_code,
    lookup_trans_type_id,
)
from mcp_digitalinvoice.adapter.exceptions import (
    UpstreamContractError,
    AuthenticationError,
    UpstreamServerError,
    AdapterError,
    UnknownSaleTypeError,
    UnknownProvinceError,
    AmbiguousRateError,
)
from mcp_digitalinvoice.logging import logger


class DigitalInvoicingAdapter:
    def __init__(
        self,
        base_url: Optional[str] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = (base_url or settings.digital_invoicing_base_url).rstrip("/")
        self._client = http_client

    def _get_headers(self) -> Dict[str, str]:
        """Browser-like headers for same-origin compliance."""
        return {
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
        }

    async def _request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Helper to send HTTP requests using an httpx client."""
        url = f"{self.base_url}{path}"
        req_headers = self._get_headers()
        if headers:
            req_headers.update(headers)

        timeout = httpx.Timeout(settings.http_timeout_seconds)

        if self._client is not None:
            return await self._client.request(
                method, url, headers=req_headers, json=json_body, timeout=timeout
            )

        async with httpx.AsyncClient(timeout=timeout) as client:
            return await client.request(
                method, url, headers=req_headers, json=json_body
            )

    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """Perform authenticating POST /api/auth/login and capture cookie + dynamic expiry."""
        try:
            response = await self._request(
                "POST",
                "/api/auth/login",
                json_body={"email": email, "password": password},
            )
        except httpx.TimeoutException as exc:
            logger.warning("Third-party login timeout", error=str(exc))
            raise UpstreamServerError("Timeout connecting to Digital Invoicing Software.") from exc
        except httpx.RequestError as exc:
            logger.warning("Third-party login network error", error=str(exc))
            raise AdapterError("Network failure communicating with third-party service.") from exc

        if response.status_code in (400, 401, 403):
            raise AuthenticationError("Invalid login credentials provided for Digital Invoicing Software.")
        elif response.status_code >= 500:
            raise UpstreamServerError(f"Digital Invoicing Software returned server error {response.status_code}.")
        elif response.status_code != 200 and response.status_code != 201:
            raise AdapterError(f"Unexpected HTTP status {response.status_code} during login.")

        # Capture Set-Cookie header
        set_cookie_header = response.headers.get("set-cookie") or response.headers.get("Set-Cookie") or ""
        cookie_val = ""
        max_age_seconds = 7199  # Default fallback if unspecified

        if "fbr_session=" in set_cookie_header:
            match = re.search(r"fbr_session=([^;]+)", set_cookie_header)
            if match:
                cookie_val = match.group(1)

        # Parse Max-Age dynamically from header
        max_age_match = re.search(r"Max-Age=(\d+)", set_cookie_header, re.IGNORECASE)
        if max_age_match:
            max_age_seconds = int(max_age_match.group(1))

        if not cookie_val:
            # Fallback if raw header string was given or simple cookie
            cookie_val = set_cookie_header.split(";")[0] if set_cookie_header else "dummy_session"

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=max_age_seconds)

        try:
            body = response.json()
        except Exception:
            body = {}

        user_profile = body.get("user", {})
        company_profile = {}
        top_level_user_id = None
        top_level_company_id = None
        if isinstance(user_profile, dict):
            top_level_user_id = user_profile.get("id")
            top_level_company_id = user_profile.get("company_id")
            if "company" in user_profile and isinstance(user_profile["company"], dict):
                company_profile = user_profile["company"]
            elif "companies" in user_profile:
                comps = user_profile["companies"]
                if isinstance(comps, dict):
                    company_profile = comps.get("company", comps)
            if not company_profile:
                company_profile = user_profile

        # The site's own invoice-create payload requires the acting user_id and
        # company_id (confirmed via live DevTools capture of the UI's own request) —
        # these live at the top level of `user`, not inside `companies`, and were
        # previously being silently discarded here.
        if isinstance(company_profile, dict):
            company_profile = dict(company_profile)
            if top_level_company_id and "company_id" not in company_profile:
                company_profile["company_id"] = top_level_company_id
            if top_level_user_id and "user_id" not in company_profile:
                company_profile["user_id"] = top_level_user_id

        return {
            "cookie": cookie_val,
            "expires_at": expires_at,
            "max_age": max_age_seconds,
            "profile": company_profile,
            "raw_body": body,
        }

    async def create_or_update_invoice(self, cookie: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """POST /api/invoices to create a draft invoice with transient transport retry and status check."""
        headers = {"Cookie": f"fbr_session={cookie}" if not cookie.startswith("fbr_session=") else cookie}
        max_transport_retries = 2

        for attempt in range(max_transport_retries + 1):
            try:
                response = await self._request(
                    "POST", "/api/invoices", headers=headers, json_body=payload
                )
            except (httpx.TransportError, httpx.RequestError) as exc:
                logger.warning(
                    "Invoice POST transport error, retrying",
                    attempt=attempt + 1,
                    max_attempts=max_transport_retries + 1,
                    error=str(exc),
                )
                if attempt == max_transport_retries:
                    raise UpstreamContractError(
                        f"Request to Digital Invoicing Software failed after "
                        f"{max_transport_retries + 1} attempts (transport error): {exc}"
                    ) from exc
                continue

            if response.status_code in (401, 403):
                raise AuthenticationError("Session expired or unauthorized for Digital Invoicing Software.")
            elif response.status_code >= 500:
                raise UpstreamServerError(f"Digital Invoicing Software returned {response.status_code} error.")
            elif response.status_code not in (200, 201):
                raise AdapterError(f"Unexpected status code {response.status_code} during invoice creation.")

            try:
                data = response.json()
            except Exception as exc:
                raise UpstreamContractError("Response body is not valid JSON.") from exc

            if not isinstance(data, dict) or "id" not in data:
                raise UpstreamContractError("Response missing mandatory 'id' field in invoice object.")

            invoice_status = (data.get("status") or "").strip().lower()
            if invoice_status not in ("draft", ""):
                # Surface whatever reason/message/error fields the site included,
                # instead of discarding the body and guessing blindly.
                reason_keys = (
                    "message", "reason", "error", "errors", "errorMessage",
                    "validationErrors", "detail", "details",
                )
                site_reason = {k: data[k] for k in reason_keys if k in data}
                logger.warning(
                    "Invoice created with unexpected status",
                    attempt=attempt + 1,
                    status=invoice_status,
                    raw_response_body=data,
                    site_reason=site_reason or None,
                )
                if attempt < max_transport_retries:
                    continue
                reason_str = f" Site response detail: {site_reason}" if site_reason else f" Full response body: {data}"
                raise UpstreamContractError(
                    f"Invoice was created but landed in unexpected status "
                    f"'{invoice_status}' after {max_transport_retries + 1} attempts.{reason_str}"
                )

            return data

        raise UpstreamContractError(f"Invoice creation failed after {max_transport_retries + 1} attempts.")

    def _format_date_for_rate_lookup(self, invoice_date: Optional[str]) -> str:
        """Format ISO date ('2026-08-31') to target site format ('31-August-2026')."""
        if not invoice_date:
            dt = datetime.now(timezone.utc)
        else:
            try:
                dt = datetime.strptime(invoice_date, "%Y-%m-%d")
            except ValueError:
                try:
                    dt = datetime.fromisoformat(invoice_date)
                except ValueError:
                    return invoice_date
        return f"{dt.day}-{dt.strftime('%B')}-{dt.year}"

    async def fetch_sales_tax_rate(
        self, cookie: str, sale_type: str, seller_province: str, invoice_date: Optional[str] = None
    ) -> float:
        """Fetch sales tax rate options from live SaleTypeToRate endpoint."""
        trans_type_id = lookup_trans_type_id(sale_type)
        if trans_type_id is None:
            raise UnknownSaleTypeError(
                f"No known transTypeId mapping for sale type '{sale_type}'. "
                f"Add it to reference_data.py by inspecting the site's own "
                f"SaleTypeToRate call when this sale type is selected."
            )

        supplier_id = lookup_province_code(seller_province)
        if supplier_id is None:
            raise UnknownProvinceError(
                f"No known originationSupplier mapping for province '{seller_province}'."
            )

        date_str = self._format_date_for_rate_lookup(invoice_date)
        path = (
            f"/api/fbr/pdi/v2/SaleTypeToRate"
            f"?date={date_str}&transTypeId={trans_type_id}&originationSupplier={supplier_id}"
        )
        headers = {"Cookie": f"fbr_session={cookie}" if not cookie.startswith("fbr_session=") else cookie}

        try:
            response = await self._request("GET", path, headers=headers)
        except httpx.TimeoutException as exc:
            raise UpstreamServerError("Timeout fetching tax rate options from Digital Invoicing Software.") from exc
        except httpx.RequestError as exc:
            raise AdapterError("Network failure during tax rate lookup.") from exc

        if response.status_code in (401, 403):
            raise AuthenticationError("Session expired or unauthorized for Digital Invoicing Software.")
        elif response.status_code >= 500:
            raise UpstreamServerError(f"Digital Invoicing Software returned {response.status_code} on rate lookup.")
        elif response.status_code != 200:
            raise AdapterError(f"Unexpected status code {response.status_code} during tax rate lookup.")

        try:
            options = response.json()
        except Exception as exc:
            raise UpstreamContractError("Rate lookup response body is not valid JSON.") from exc

        if not isinstance(options, list) or not options:
            raise UnknownSaleTypeError(
                f"SaleTypeToRate returned no rate options for sale type '{sale_type}'."
            )

        if len(options) > 1:
            rate_list = ", ".join(f"{o.get('ratE_VALUE')}%" for o in options if "ratE_VALUE" in o)
            raise AmbiguousRateError(
                f"Multiple valid tax rates for '{sale_type}': {rate_list}. "
                f"Caller must specify which one via the item's 'rate' field."
            )

        first_val = options[0].get("ratE_VALUE")
        if first_val is None:
            raise UpstreamContractError("Rate option missing 'ratE_VALUE' key.")

        return float(first_val)

    async def validate_invoice(self, cookie: str, invoice_id: str) -> Dict[str, Any]:
        """Stub for validate_invoice - out of scope for current build."""
        raise NotImplementedError("Validate Invoice is out of scope due to upstream 500 error.")

    async def submit_invoice(self, cookie: str, invoice_id: str) -> Dict[str, Any]:
        """Stub for submit_invoice - out of scope for current build."""
        raise NotImplementedError("Submit Invoice is out of scope for current build.")
