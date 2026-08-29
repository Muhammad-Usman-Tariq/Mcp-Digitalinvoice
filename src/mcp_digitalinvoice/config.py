"""Central application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database & Redis
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mcp_invoice"
    redis_url: str = "redis://localhost:6379/0"

    # Security
    encryption_key: str = "k5_3sZ8XfD-t4K3qR8W1yU9vX2zL7nB4mQ6pP0oI8aE="

    # Target Third-Party Service
    digital_invoicing_base_url: str = "https://www.digitalinvoicingsoftware.com"
    digital_invoicing_env: str = "sandbox"

    # HTTP Client Configuration
    http_timeout_seconds: float = 15.0
    max_retries: int = 2
    login_rate_limit_seconds: int = 30
    cookie_refresh_buffer_seconds: int = 60

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


settings = Settings()
