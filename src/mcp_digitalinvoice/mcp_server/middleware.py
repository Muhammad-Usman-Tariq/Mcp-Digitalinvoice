"""Per-request MCP API key propagation for the Streamable-HTTP transport.

Native MCP tool functions (fill_invoice/validate_invoice/submit_invoice in
mcp_server/server.py) have no direct access to the underlying HTTP request,
so they can't read the caller's X-MCP-API-Key header themselves. This
module captures that header once, per request, via a thin ASGI middleware,
and stores it in a contextvar that _resolve_tenant_id() reads from.
"""

import contextvars
from typing import Optional

mcp_api_key_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "mcp_api_key_ctx", default=None
)


class MCPAuthHeaderMiddleware:
    """Extracts the caller's MCP API key from the incoming request and
    stores it in `mcp_api_key_ctx` for the duration of that request.

    Accepts either:
      - X-MCP-API-Key: <key>
      - Authorization: Bearer <key>
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw_key = None
        for name, value in scope.get("headers", []):
            if name == b"x-mcp-api-key":
                raw_key = value.decode("latin-1")
                break
            if name == b"authorization" and value.lower().startswith(b"bearer "):
                raw_key = value[7:].decode("latin-1")

        token = mcp_api_key_ctx.set(raw_key)
        try:
            await self.app(scope, receive, send)
        finally:
            mcp_api_key_ctx.reset(token)
