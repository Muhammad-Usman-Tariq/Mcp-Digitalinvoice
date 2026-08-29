"""Tests for security module encryption, API key hashing, and log redaction."""

from mcp_digitalinvoice.security import (
    encrypt_secret,
    decrypt_secret,
    generate_mcp_api_key,
    hash_api_key,
)
from mcp_digitalinvoice.logging import redact_sensitive_data


def test_encryption_decryption(synthetic_tenant_data):
    plaintext = synthetic_tenant_data["password"]
    encrypted = encrypt_secret(plaintext)

    assert encrypted != plaintext
    assert isinstance(encrypted, str)

    decrypted = decrypt_secret(encrypted)
    assert decrypted == plaintext


def test_empty_secret_encryption():
    assert encrypt_secret("") == ""
    assert decrypt_secret("") == ""


def test_api_key_generation_and_hashing():
    raw_key = generate_mcp_api_key()
    assert raw_key.startswith("mcp_")

    hashed = hash_api_key(raw_key)
    assert len(hashed) == 64  # SHA-256 hex string length
    assert hashed == hash_api_key(raw_key)


def test_log_redaction_processor(synthetic_tenant_data):
    event_dict = {
        "event": "login attempt",
        "email": synthetic_tenant_data["email"],
        "password": synthetic_tenant_data["password"],
        "cookie": "fbr_session=secret_token",
        "nested": {"api_key": "mcp_secret_key", "safe_param": "visible"},
    }

    redacted = redact_sensitive_data(None, "info", event_dict)

    assert redacted["email"] == "[REDACTED]"
    assert redacted["password"] == "[REDACTED]"
    assert redacted["cookie"] == "[REDACTED]"
    assert redacted["nested"]["api_key"] == "[REDACTED]"
    assert redacted["nested"]["safe_param"] == "visible"
