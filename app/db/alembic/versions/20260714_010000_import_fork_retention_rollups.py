"""Import the retired fork retention rollups.

Revision ID: 20260714_010000_import_fork_retention_rollups
Revises: 20260713_020000_add_model_registry_snapshot
Create Date: 2026-07-14
"""

from __future__ import annotations

from math import isclose

import sqlalchemy as sa
from alembic import op

revision = "20260714_010000_import_fork_retention_rollups"
down_revision = "20260713_020000_add_model_registry_snapshot"
branch_labels = None
depends_on = None

_LEGACY_TABLE = "request_log_daily_aggregates"
_REQUIRED_COLUMNS = {
    "account_id",
    "api_key_id",
    "request_kind",
    "is_deleted",
    "request_count",
    "input_tokens",
    "effective_output_tokens",
    "cached_input_tokens",
    "cost_usd",
    "account_request_count",
    "account_input_tokens",
    "account_output_tokens",
    "account_cached_input_tokens",
    "account_cost_usd",
}


def _totals(table: str) -> tuple[int, int, int, int, float]:
    row = (
        op.get_bind()
        .execute(
            sa.text(
                f"""SELECT COALESCE(SUM(request_count), 0),
                       COALESCE(SUM(input_tokens), 0),
                       COALESCE(SUM(output_tokens), 0),
                       COALESCE(SUM(cached_input_tokens), 0),
                       COALESCE(SUM(total_cost_usd), 0.0)
                FROM {table}"""
            )
        )
        .one()
    )
    return int(row[0]), int(row[1]), int(row[2]), int(row[3]), float(row[4])


def _assert_totals(
    label: str, expected: tuple[int, int, int, int, float], actual: tuple[int, int, int, int, float]
) -> None:
    if expected[:4] != actual[:4] or not isclose(expected[4], actual[4], rel_tol=1e-12, abs_tol=1e-9):
        raise RuntimeError(f"fork {label} rollup import parity failed: expected={expected!r} actual={actual!r}")


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if _LEGACY_TABLE not in inspector.get_table_names():
        return

    columns = {str(column["name"]) for column in inspector.get_columns(_LEGACY_TABLE)}
    missing = sorted(_REQUIRED_COLUMNS - columns)
    if missing:
        raise RuntimeError(f"fork retention table is missing hardened columns: {', '.join(missing)}")

    state = connection.execute(
        sa.text("SELECT folded_through FROM account_usage_rollup_state WHERE id = 1")
    ).scalar_one_or_none()
    if state is None or not str(state).startswith("1970-01-01 00:00:00"):
        raise RuntimeError("fork rollup import requires an epoch upstream fold watermark")

    connection.execute(sa.text("DELETE FROM account_usage_rollups"))
    connection.execute(sa.text("DELETE FROM api_key_usage_rollups"))

    account_rows = connection.execute(
        sa.text(
            """SELECT d.account_id,
                       SUM(d.account_request_count), SUM(d.account_input_tokens),
                       SUM(d.account_output_tokens), SUM(d.account_cached_input_tokens),
                       SUM(d.account_cost_usd)
                FROM request_log_daily_aggregates d
                JOIN accounts a ON a.id = d.account_id
                WHERE d.account_id IS NOT NULL
                  AND d.request_kind NOT IN ('warmup', 'limit_warmup')
                  AND d.is_deleted = false
                GROUP BY d.account_id"""
        )
    ).all()
    for key, requests, inputs, outputs, cached, cost in account_rows:
        connection.execute(
            sa.text(
                """INSERT INTO account_usage_rollups
                   (account_id, request_count, input_tokens, output_tokens, cached_input_tokens, total_cost_usd)
                   VALUES (:key, :requests, :inputs, :outputs, :cached, :cost)"""
            ),
            {"key": key, "requests": requests, "inputs": inputs, "outputs": outputs, "cached": cached, "cost": cost},
        )

    api_key_rows = connection.execute(
        sa.text(
            """SELECT d.api_key_id,
                       SUM(d.request_count), SUM(d.input_tokens),
                       SUM(d.effective_output_tokens), SUM(d.cached_input_tokens),
                       SUM(d.cost_usd)
                FROM request_log_daily_aggregates d
                JOIN api_keys k ON k.id = d.api_key_id
                WHERE d.api_key_id IS NOT NULL
                  AND d.request_kind NOT IN ('warmup', 'limit_warmup')
                GROUP BY d.api_key_id"""
        )
    ).all()
    for key, requests, inputs, outputs, cached, cost in api_key_rows:
        connection.execute(
            sa.text(
                """INSERT INTO api_key_usage_rollups
                   (api_key_id, request_count, input_tokens, output_tokens, cached_input_tokens, total_cost_usd)
                   VALUES (:key, :requests, :inputs, :outputs, :cached, :cost)"""
            ),
            {"key": key, "requests": requests, "inputs": inputs, "outputs": outputs, "cached": cached, "cost": cost},
        )

    expected_accounts = (
        sum(int(row[1]) for row in account_rows),
        sum(int(row[2]) for row in account_rows),
        sum(int(row[3]) for row in account_rows),
        sum(int(row[4]) for row in account_rows),
        sum(float(row[5]) for row in account_rows),
    )
    expected_keys = (
        sum(int(row[1]) for row in api_key_rows),
        sum(int(row[2]) for row in api_key_rows),
        sum(int(row[3]) for row in api_key_rows),
        sum(int(row[4]) for row in api_key_rows),
        sum(float(row[5]) for row in api_key_rows),
    )
    _assert_totals("account", expected_accounts, _totals("account_usage_rollups"))
    _assert_totals("API-key", expected_keys, _totals("api_key_usage_rollups"))
    op.drop_table(_LEGACY_TABLE)


def downgrade() -> None:
    # The retired dimensional table is intentionally not recreated. The
    # imported upstream lifetime rollups remain valid on downgrade.
    pass
