"""Report service: builds Reports-page-equivalent summaries from the tenant's invoice list.

IMPORTANT: The target site has no separate "reports" API. Its own Reports page loads
the full invoice list once and does all date-filtering/grouping/summing client-side in
the browser. This service replicates that exact behavior server-side so results match
the UI 1:1.
"""

from datetime import datetime
from typing import Optional
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_digitalinvoice.session.manager import SessionManager
from mcp_digitalinvoice.adapter.client import DigitalInvoicingAdapter
from mcp_digitalinvoice.adapter.exceptions import (
    AuthenticationError,
    UpstreamServerError,
    UpstreamContractError,
    AdapterError,
    ConnectionBrokenError,
)
from mcp_digitalinvoice.models.schemas import (
    ReportsInput,
    ReportsResult,
    ReportSummary,
    ReportGroup,
    ReportRow,
)
from mcp_digitalinvoice.logging import logger

_VALID_GROUP_BY = {
    "none", "date", "voucher_no", "invoice_number", "customer", "sale_type", "item_name",
}


class ReportService:
    def __init__(
        self,
        db: AsyncSession,
        redis: Optional[Redis] = None,
        adapter: Optional[DigitalInvoicingAdapter] = None,
    ):
        self.db = db
        self.redis = redis
        self.adapter = adapter or DigitalInvoicingAdapter()
        self.session_manager = SessionManager(db, redis, self.adapter)

    async def get_reports(self, tenant_id, input_data: ReportsInput) -> ReportsResult:
        group_by = (input_data.groupBy or "none").strip().lower()
        if group_by not in _VALID_GROUP_BY:
            return ReportsResult(
                status="failed",
                error=f"Invalid groupBy '{group_by}'. Must be one of: {sorted(_VALID_GROUP_BY)}.",
            )

        try:
            cookie, profile = await self.session_manager.get_valid_cookie_and_profile(tenant_id)
        except (AuthenticationError, ConnectionBrokenError) as exc:
            return ReportsResult(status="failed", error=str(exc))

        company_id = profile.get("company_id") if isinstance(profile, dict) else None
        if not company_id:
            return ReportsResult(
                status="failed",
                error="Could not resolve company_id for this tenant's Digital Invoicing Software profile.",
            )

        try:
            invoices = await self.adapter.fetch_invoices(cookie, company_id)
        except (AuthenticationError, UpstreamServerError, UpstreamContractError, AdapterError) as exc:
            return ReportsResult(status="failed", error=str(exc))

        date_from = self._parse_date(input_data.dateFrom)
        date_to = self._parse_date(input_data.dateTo)

        flat_rows = []
        for idx, inv in enumerate(invoices, start=1):
            inv_date_str = inv.get("invoice_date")
            inv_date = self._parse_date(inv_date_str)
            if date_from and (not inv_date or inv_date < date_from):
                continue
            if date_to and (not inv_date or inv_date > date_to):
                continue

            items = inv.get("invoice_items") or [{}]
            for item in items:
                quantity = item.get("quantity") or 0
                amount = item.get("value_sales_excluding_st") or 0
                gst = item.get("sales_tax_applicable") or 0
                net = item.get("total_value")
                if net is None:
                    net = (amount or 0) + (gst or 0)

                flat_rows.append(ReportRow(
                    voucher_no=idx,
                    invoice_ref_no=inv.get("invoice_ref_no") or "N/A",
                    sale_type=item.get("sale_type"),
                    invoice_date=inv_date_str,
                    customer=inv.get("buyer_business_name"),
                    item_name=item.get("product_description") or None,
                    quantity=quantity,
                    amount=amount,
                    gst=gst,
                    net_amount=net,
                ))

        summary = ReportSummary(
            total_groups=0,
            total_items=len(flat_rows),
            total_quantity=sum(r.quantity or 0 for r in flat_rows),
            total_amount=sum(r.amount or 0 for r in flat_rows),
            total_gst=sum(r.gst or 0 for r in flat_rows),
            net_amount=sum(r.net_amount or 0 for r in flat_rows),
        )

        key_fn = self._group_key_fn(group_by)
        groups_map = {}
        for row in flat_rows:
            key = key_fn(row) or "N/A"
            groups_map.setdefault(key, []).append(row)

        groups = [
            ReportGroup(group_key=key, row_count=len(rows), rows=rows)
            for key, rows in sorted(groups_map.items())
        ]
        summary.total_groups = len(groups)

        return ReportsResult(status="ok", summary=summary, groups=groups)

    @staticmethod
    def _parse_date(value: Optional[str]):
        if not value:
            return None
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _group_key_fn(group_by: str):
        return {
            "none": lambda r: "All",
            "date": lambda r: r.invoice_date,
            "voucher_no": lambda r: str(r.voucher_no),
            "invoice_number": lambda r: r.invoice_ref_no,
            "customer": lambda r: r.customer,
            "sale_type": lambda r: r.sale_type,
            "item_name": lambda r: r.item_name,
        }[group_by]
