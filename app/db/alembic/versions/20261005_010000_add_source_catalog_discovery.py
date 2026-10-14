"""Separate automatic catalog ownership from cached model rows."""

import sqlalchemy as sa
from alembic import op

revision = "20261005_010000_add_source_catalog_discovery"
down_revision = "20261005_000000_add_model_source_api_key_whitelist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("model_sources")}
    if "auto_discover_models" not in columns:
        op.add_column(
            "model_sources", sa.Column("auto_discover_models", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        op.execute(
            sa.text(
                "UPDATE model_sources SET auto_discover_models = true "
                "WHERE NOT EXISTS (SELECT 1 FROM model_source_models WHERE source_id = model_sources.id)"
            )
        )
    if "catalog_revision" not in columns:
        op.add_column("model_sources", sa.Column("catalog_revision", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("model_sources") as batch:
        batch.drop_column("catalog_revision")
        batch.drop_column("auto_discover_models")
