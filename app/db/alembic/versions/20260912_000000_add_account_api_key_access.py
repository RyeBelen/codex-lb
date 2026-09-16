"""Reserve accounts for explicitly permitted API keys."""

import sqlalchemy as sa
from alembic import op

revision = "20260912_000000_add_account_api_key_access"
down_revision = "20260908_000000_add_api_key_denied_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    # Legacy revision remapping can replay migrations against an existing schema.
    if "api_key_access_restricted" not in {column["name"] for column in inspector.get_columns("accounts")}:
        op.add_column(
            "accounts",
            sa.Column("api_key_access_restricted", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if not inspector.has_table("account_api_key_grants"):
        op.create_table(
            "account_api_key_grants",
            sa.Column("account_id", sa.String(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("api_key_id", sa.String(), sa.ForeignKey("api_keys.id", ondelete="CASCADE"), primary_key=True),
        )
    if "ix_account_api_key_grants_api_key_id" not in {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes("account_api_key_grants")
    }:
        op.create_index("ix_account_api_key_grants_api_key_id", "account_api_key_grants", ["api_key_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("account_api_key_grants"):
        op.drop_table("account_api_key_grants")
    if "api_key_access_restricted" in {column["name"] for column in inspector.get_columns("accounts")}:
        with op.batch_alter_table("accounts") as batch:
            batch.drop_column("api_key_access_restricted")
