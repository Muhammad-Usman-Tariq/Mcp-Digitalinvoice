"""Structured logging setup with mandatory redaction filter for sensitive keys."""

import logging
import sys
import structlog

REDACTED_KEYS = {
    "password",
    "email",
    "cookie",
    "fbr_session",
    "api_key",
    "secret",
    "authorization",
    "encrypted_email",
    "encrypted_password",
    "encrypted_cookie",
    "raw_key",
    "key",
    "token",
}


def redact_sensitive_data(logger, method_name, event_dict):
    """Processor to recursively redact sensitive key-value pairs in log records."""
    def _redact_value(key, val):
        if any(sensitive in key.lower() for sensitive in REDACTED_KEYS):
            return "[REDACTED]"
        if isinstance(val, dict):
            return {k: _redact_value(k, v) for k, v in val.items()}
        if isinstance(val, list):
            return [_redact_value(key, item) for item in val]
        return val

    return {k: _redact_value(k, v) for k, v in event_dict.items()}


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog processors and standard logging handler."""
    logging_level = getattr(logging, log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            redact_sensitive_data,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger()
