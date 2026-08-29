"""Initial schema migration for tenants, credentials, sessions, keys, and jobs.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-08-29 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tenants',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'tenant_credentials',
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('encrypted_email', sa.Text(), nullable=False),
        sa.Column('encrypted_password', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tenant_id')
    )

    op.create_table(
        'tenant_sessions',
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('encrypted_cookie', sa.Text(), nullable=False),
        sa.Column('seller_profile', sa.JSON(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_refreshed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('tenant_id')
    )

    op.create_table(
        'mcp_api_keys',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('hashed_key', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_mcp_api_keys_hashed_key'), 'mcp_api_keys', ['hashed_key'], unique=False)

    op.create_table(
        'invoice_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('source_document_hash', sa.String(length=128), nullable=False),
        sa.Column('extracted_payload', sa.JSON(), nullable=False),
        sa.Column('remote_invoice_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoice_jobs_source_document_hash'), 'invoice_jobs', ['source_document_hash'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_invoice_jobs_source_document_hash'), table_name='invoice_jobs')
    op.drop_table('invoice_jobs')
    op.drop_index(op.f('ix_mcp_api_keys_hashed_key'), table_name='mcp_api_keys')
    op.drop_table('mcp_api_keys')
    op.drop_table('tenant_sessions')
    op.drop_table('tenant_credentials')
    op.drop_table('tenants')
