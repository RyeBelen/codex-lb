from __future__ import annotations

import sqlite3

import pytest
from alembic import command

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

pytestmark = pytest.mark.integration


def test_astra_migration_preserves_existing_keys_and_roundtrips(tmp_path):
    path = tmp_path / "astra.db"
    url = f"sqlite+aiosqlite:///{path}"
    parent = "20260830_000000_add_quota_warmup_claim_expiry"
    run_upgrade(url, parent, bootstrap_legacy=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO api_keys (id, name, key_hash, key_prefix, is_active, created_at) "
            "VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)",
            ("existing", "Existing", "test-hash", "test-prefix"),
        )
    run_upgrade(url, "head", bootstrap_legacy=False)
    assert not check_schema_drift(url)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT allow_gpt6_astra FROM api_keys").fetchone() == (0,)
        connection.execute("UPDATE api_keys SET allow_gpt6_astra = 1")
    command.downgrade(_build_alembic_config(url), parent)
    with sqlite3.connect(path) as connection:
        assert "allow_gpt6_astra" not in {row[1] for row in connection.execute("PRAGMA table_info(api_keys)")}
        assert connection.execute("SELECT name FROM api_keys").fetchone() == ("Existing",)
    run_upgrade(url, "head", bootstrap_legacy=False)
    assert not check_schema_drift(url)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT allow_gpt6_astra FROM api_keys").fetchone() == (0,)
