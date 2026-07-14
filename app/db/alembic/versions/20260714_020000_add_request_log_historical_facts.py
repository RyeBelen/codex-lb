"""add compact request-log historical facts

Revision ID: 20260714_020000_add_request_log_historical_facts
Revises: 20260714_010000_import_fork_retention_rollups
Create Date: 2026-07-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260714_020000_add_request_log_historical_facts"
down_revision = "20260714_010000_import_fork_retention_rollups"
branch_labels = None
depends_on = None

_TABLE = "request_log_historical_facts"
_INDEXES = (
    ("idx_request_history_requested_at_id", ["requested_at", "request_log_id"]),
    ("idx_request_history_account_time", ["account_id", "requested_at"]),
    ("idx_request_history_api_key_time", ["api_key_id", "requested_at"]),
    (
        "idx_request_history_response_owner",
        ["request_id", "api_key_id", sa.text("requested_at DESC"), sa.text("request_log_id DESC")],
    ),
)


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("request_log_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.String(), nullable=True),
        sa.Column("api_key_id", sa.String(), nullable=True),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("requested_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("reasoning_effort", sa.String(), nullable=True),
        sa.Column("service_tier", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("useragent_group", sa.String(), nullable=True),
        sa.Column("request_kind", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error_code", sa.String(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cached_input_tokens", sa.Integer(), nullable=True),
        sa.Column("reasoning_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("latency_first_token_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("request_log_id"),
    )
    for name, columns in _INDEXES:
        op.create_index(name, _TABLE, columns, unique=False)


def downgrade() -> None:
    for name, _columns in reversed(_INDEXES):
        op.drop_index(name, table_name=_TABLE)
    op.drop_table(_TABLE)
