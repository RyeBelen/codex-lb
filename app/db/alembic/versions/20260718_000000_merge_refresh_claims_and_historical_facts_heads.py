"""merge refresh claims and historical request facts migration heads

Revision ID: 20260718_000000_merge_refresh_claims_and_historical_facts_heads
Revises:
- 20260713_040000_add_account_refresh_claims
- 20260714_020000_add_request_log_historical_facts
Create Date: 2026-07-18 00:00:00.000000
"""

from __future__ import annotations

revision = "20260718_000000_merge_refresh_claims_and_historical_facts_heads"
down_revision = (
    "20260713_040000_add_account_refresh_claims",
    "20260714_020000_add_request_log_historical_facts",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
