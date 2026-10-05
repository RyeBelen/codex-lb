"""Persist source-side key IDs without broadening access on key deletion."""

import sqlalchemy as sa
from alembic import op

revision = "20261005_000000_add_model_source_api_key_whitelist"
down_revision = "20260930_000000_add_weekly_empty_auto_redeem"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("model_sources")}
    if "allowed_api_key_ids_json" not in columns:
        op.add_column("model_sources", sa.Column("allowed_api_key_ids_json", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("model_sources") as batch:
        batch.drop_column("allowed_api_key_ids_json")
