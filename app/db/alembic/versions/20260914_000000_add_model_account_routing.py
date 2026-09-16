"""Restrict individual models to explicitly selected upstream accounts."""

import sqlalchemy as sa
from alembic import op

revision = "20260914_000000_add_model_account_routing"
down_revision = "20260912_000000_add_account_api_key_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("model_account_policies"):
        op.create_table("model_account_policies", sa.Column("model", sa.String(128), primary_key=True))
    if not inspector.has_table("model_account_grants"):
        op.create_table(
            "model_account_grants",
            sa.Column(
                "model",
                sa.String(128),
                sa.ForeignKey("model_account_policies.model", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True),
        )
    if "ix_model_account_grants_account_id" not in {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes("model_account_grants")
    }:
        op.create_index("ix_model_account_grants_account_id", "model_account_grants", ["account_id"])


def downgrade() -> None:
    op.drop_table("model_account_grants")
    op.drop_table("model_account_policies")
