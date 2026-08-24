"""add bounded API-key verbose request capture

Revision ID: 20260824_000000_add_api_key_verbose_capture
Revises: 20260718_000000_merge_refresh_claims_and_historical_facts_heads
Create Date: 2026-08-24
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260824_000000_add_api_key_verbose_capture"
down_revision = "20260718_000000_merge_refresh_claims_and_historical_facts_heads"
branch_labels = None
depends_on = None

_TABLE = "api_key_verbose_captures"


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _has_column("api_keys", "verbose_capture_remaining"):
        op.add_column(
            "api_keys",
            sa.Column(
                "verbose_capture_remaining",
                sa.Integer(),
                server_default=sa.text("0"),
                nullable=False,
            ),
        )

    if not _has_table(_TABLE):
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("api_key_id", sa.String(), nullable=False),
            sa.Column("request_id", sa.String(), nullable=False),
            sa.Column("method", sa.String(), nullable=False),
            sa.Column("path", sa.Text(), nullable=False),
            sa.Column("content_type", sa.String(), nullable=False),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.Column("truncated", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("captured_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("api_key_id", "request_id", name="uq_api_key_verbose_capture_request"),
        )
    if not _has_index(_TABLE, "idx_api_key_verbose_captures_captured_at"):
        op.create_index("idx_api_key_verbose_captures_captured_at", _TABLE, ["captured_at"], unique=False)


def downgrade() -> None:
    if _has_table(_TABLE):
        if _has_index(_TABLE, "idx_api_key_verbose_captures_captured_at"):
            op.drop_index("idx_api_key_verbose_captures_captured_at", table_name=_TABLE)
        op.drop_table(_TABLE)
    if _has_column("api_keys", "verbose_capture_remaining"):
        op.drop_column("api_keys", "verbose_capture_remaining")
