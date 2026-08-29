"""Security helpers for encryption, decryption, and API key hashing."""

import hashlib
import secrets
from cryptography.fernet import Fernet
from mcp_digitalinvoice.config import settings


def _get_fernet() -> Fernet:
    """Return a Fernet cipher instance using the configured key."""
    key = settings.encryption_key.encode("utf-8")
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret string returning a fernet token string."""
    if not plaintext:
        return ""
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a fernet token string returning plaintext."""
    if not ciphertext:
        return ""
    fernet = _get_fernet()
    return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def generate_mcp_api_key() -> str:
    """Generate a high-entropy raw API key for MCP clients."""
    return f"mcp_{secrets.token_urlsafe(32)}"


def hash_api_key(raw_key: str) -> str:
    """Return SHA-256 hex digest of the raw API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
