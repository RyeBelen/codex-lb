from __future__ import annotations

import sqlite3

import pytest
from alembic import command
from alembic.script import ScriptDirectory

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

pytestmark = pytest.mark.integration


def test_source_whitelist_migration_preserves_sources_and_roundtrips(tmp_path):
    path = tmp_path / "source-access.db"
    url = f"sqlite+aiosqlite:///{path}"
    parent = "20260930_000000_add_weekly_empty_auto_redeem"
    run_upgrade(url, parent, bootstrap_legacy=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO model_sources (id,name,base_url) VALUES ('src','Original','http://localhost/v1')"
        )
        connection.execute("INSERT INTO model_source_models (source_id,model) VALUES ('src','local-model')")
    config = _build_alembic_config(url)
    assert ScriptDirectory.from_config(config).get_heads() == ["20261005_000000_add_model_source_api_key_whitelist"]
    run_upgrade(url, "head", bootstrap_legacy=False)
    assert not check_schema_drift(url)
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT allowed_api_key_ids_json FROM model_sources").fetchone() == (None,)
        connection.execute("UPDATE model_sources SET allowed_api_key_ids_json='[\"test-key\"]'")
    command.downgrade(config, parent)
    with sqlite3.connect(path) as connection:
        assert "allowed_api_key_ids_json" not in {
            row[1] for row in connection.execute("PRAGMA table_info(model_sources)")
        }
        assert connection.execute("SELECT name FROM model_sources").fetchone() == ("Original",)
        assert connection.execute("SELECT model FROM model_source_models").fetchone() == ("local-model",)
    run_upgrade(url, "head", bootstrap_legacy=False)
    assert not check_schema_drift(url)
