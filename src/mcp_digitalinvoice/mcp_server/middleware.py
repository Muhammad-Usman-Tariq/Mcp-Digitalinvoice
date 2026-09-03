"""Per-request MCP API key propagation for the Streamable-HTTP transport.

Native MCP tool functions (fill_invoice/validate_invoice/submit_invoice in
mcp_server/server.py) have no direct access to the underlying HTTP request,
so they can't read the caller's API key header themselves. This
module captures that header once, per request, via a thin ASGI middleware,
and stores it in a contextvar that _resolve_tenant_id() reads from.

Accepts (in priority order):
  1. X-MCP-API-Key: <key>
  2. x-api-key: <key>
  3. Authorization: Bearer <key>
"""

import contextvars
from typing import Optional

mcp_api_key_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "mcp_api_key_ctx", default=None
)


class MCPAuthHeaderMiddleware:
    """Extracts the caller's MCP API key from the incoming request and
    stores it in `mcp_api_key_ctx` for the duration of that request.

    Accepts (in priority order):
      1. X-MCP-API-Key: <key>
      2. x-api-key: <key>
      3. Authorization: Bearer <key>
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        raw_key = None
        if b"x-mcp-api-key" in headers:
            raw_key = headers[b"x-mcp-api-key"].decode("latin-1")
        elif b"x-api-key" in headers:
            raw_key = headers[b"x-api-key"].decode("latin-1")
        elif b"authorization" in headers:
            auth_val = headers[b"authorization"]
            if auth_val.lower().startswith(b"bearer "):
                raw_key = auth_val[7:].decode("latin-1")

        token = mcp_api_key_ctx.set(raw_key)
        try:
            await self.app(scope, receive, send)
        finally:
            mcp_api_key_ctx.reset(token)

