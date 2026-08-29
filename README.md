# Multi-Tenant Invoice Autofill MCP Server

A Python backend service enabling function-calling or MCP-capable LLMs (Claude, Gemini, GPT, etc.) to autofill and save invoices on Digital Invoicing Software on behalf of tenants.

## Features

- **Dual Transport Support**: Exposed via standard MCP protocol (stdio / Streamable HTTP) and REST API (FastAPI) with OpenAPI schema.
- **Multi-Tenancy & Auth**: Per-tenant credential encryption, custom MCP API keys, and isolated session management.
- **Resilient Adapter**: Encapsulated HTTP adapter replicating browser headers, with reactive session refresh and dynamic cookie expiry parsing.
- **Idempotency & Concurrency**: Deduplication via document hash and per-tenant Redis distributed locking (`lock:tenant:{id}`).
- **Privacy First**: Mandatory structured log redaction layer scrubbing passwords, cookies, keys, and tokens.
- **Zero Hardcoded Values**: No credentials or business identities baked into code, comments, or tests; full synthetic test data generation.

## Local Prerequisites

- Python 3.12+
- Docker & Docker Compose (for local Postgres & Redis)

## Getting Started

### 1. Environment Setup

Copy `.env.example` to `.env` and set local variables:

```bash
cp .env.example .env
```

### 2. Launch Local Database & Redis

```bash
docker-compose up -d
```

### 3. Install Dependencies

```bash
python -m venv .venv
# Windows:
.\.venv\Scripts\pip install -r requirements.txt
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Run Migrations

```bash
.\.venv\Scripts\alembic upgrade head
```

### 5. Start the Server

```bash
# Start FastAPI REST server:
.\.venv\Scripts\uvicorn mcp_digitalinvoice.main:app --reload --port 8000

# Run MCP stdio server:
.\.venv\Scripts\python -m mcp_digitalinvoice.mcp_server.server
```

## Security

> [!CAUTION]
> **Encryption Key Management**: The `ENCRYPTION_KEY` environment variable must be set to a secure 32-byte base64-encoded Fernet key. Application startup will fail immediately if `ENCRYPTION_KEY` is not provided. If an encryption key was ever used to encrypt real tenant data and is suspected of exposure, that data must be re-encrypted under a freshly generated key, since the old key must be considered compromised.

## Workflows

### Tenant Onboarding (`connect_account`)

1. Call `connect_account` with the tenant's Digital Invoicing Software login email, password, and business name.
2. The server encrypts credentials, validates them via an initial login, and returns a unique `mcp_api_key`.
3. Provide this `mcp_api_key` to the LLM (as a Bearer token or header) for subsequent tool invocations.

### Invoice Autofill (`fill_invoice`)

The LLM invokes `fill_invoice` with extracted invoice JSON payload (`buyer`, `items`, `meta`). The service validates required fields, enforces single-document sequencing, checks idempotency, resolves tenant session, maps payload to downstream shape, and creates the invoice draft.

## Running Tests

```bash
.\.venv\Scripts\pytest -v tests/
```
