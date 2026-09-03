"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from mcp_digitalinvoice.api.routes import router
from mcp_digitalinvoice.api.setup_routes import setup_router
from mcp_digitalinvoice.config import settings
from mcp_digitalinvoice.logging import configure_logging, logger
from mcp_digitalinvoice.mcp_server.server import mcp
from mcp_digitalinvoice.mcp_server.middleware import MCPAuthHeaderMiddleware
from mcp.server.transport_security import TransportSecuritySettings

_allowed_hosts = [h.strip() for h in settings.mcp_allowed_hosts.split(",") if h.strip()]

mcp.settings.transport_security = TransportSecuritySettings(
    enable_dns_rebinding_protection=True,
    allowed_hosts=_allowed_hosts,
    allowed_origins=[f"https://{h}" for h in _allowed_hosts],
)
mcp_asgi_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    logger.info("Starting Multi-Tenant Invoice Autofill Server", env=settings.digital_invoicing_env)
    async with mcp.session_manager.run():
        yield
    logger.info("Shutting down Multi-Tenant Invoice Autofill Server")


app = FastAPI(
    title="Multi-Tenant Invoice Autofill API",
    description="REST & Function-Calling interface for Digital Invoicing Software autofill server",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)
app.include_router(setup_router)



@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "environment": settings.digital_invoicing_env}


app.mount("/", MCPAuthHeaderMiddleware(mcp_asgi_app))

