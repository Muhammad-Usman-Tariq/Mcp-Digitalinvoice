"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from mcp_digitalinvoice.api.routes import router
from mcp_digitalinvoice.config import settings
from mcp_digitalinvoice.logging import configure_logging, logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    logger.info("Starting Multi-Tenant Invoice Autofill Server", env=settings.digital_invoicing_env)
    yield
    logger.info("Shutting down Multi-Tenant Invoice Autofill Server")


app = FastAPI(
    title="Multi-Tenant Invoice Autofill API",
    description="REST & Function-Calling interface for Digital Invoicing Software autofill server",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "environment": settings.digital_invoicing_env}
