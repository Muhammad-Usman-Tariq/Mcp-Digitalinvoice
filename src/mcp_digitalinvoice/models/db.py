"""SQLAlchemy ORM models representing the database schema."""

from datetime import datetime, timezone
import uuid
from typing import Optional, Any
from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    UUID,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return current UTC timestamp without timezone offset issues."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    credentials: Mapped[Optional["TenantCredential"]] = relationship(
        "TenantCredential", back_populates="tenant", cascade="all, delete-orphan", uselist=False
    )
    session: Mapped[Optional["TenantSession"]] = relationship(
        "TenantSession", back_populates="tenant", cascade="all, delete-orphan", uselist=False
    )
    api_keys: Mapped[list["MCPAPIKey"]] = relationship(
        "MCPAPIKey", back_populates="tenant", cascade="all, delete-orphan"
    )
    invoice_jobs: Mapped[list["InvoiceJob"]] = relationship(
        "InvoiceJob", back_populates="tenant", cascade="all, delete-orphan"
    )


class TenantCredential(Base):
    __tablename__ = "tenant_credentials"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    encrypted_email: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_password: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="credentials")


class TenantSession(Base):
    __tablename__ = "tenant_sessions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    encrypted_cookie: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    last_refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="session")


class MCPAPIKey(Base):
    __tablename__ = "mcp_api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    hashed_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="api_keys")


class InvoiceJob(Base):
    __tablename__ = "invoice_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    source_document_hash: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    extracted_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    remote_invoice_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    error_detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="invoice_jobs")
