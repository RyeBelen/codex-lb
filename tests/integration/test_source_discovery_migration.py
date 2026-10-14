from __future__ import annotations

import sqlite3

import pytest
from alembic import command
from alembic.script import ScriptDirectory

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

pytestmark = pytest.mark.integration


def test_discovery_migration_backfills_ownership_and_roundtrips(tmp_path):
    path = tmp_path / "catalog-discovery.db"
    url = f"sqlite+aiosqlite:///{path}"
    parent = "20261005_000000_add_model_source_api_key_whitelist"
    run_upgrade(url, parent, bootstrap_legacy=True)
    with sqlite3.connect(path) as connection:
        connection.executemany(
            "INSERT INTO model_sources (id,name,base_url) VALUES (?,?,?)",
            [("empty", "Empty", "http://localhost/v1"), ("manual", "Manual", "http://localhost/v1")],
        )
        connection.execute("INSERT INTO model_source_models (source_id,model) VALUES ('manual','fixed')")
    config = _build_alembic_config(url)
    assert ScriptDirectory.from_config(config).get_heads() == ["20261005_010000_add_source_catalog_discovery"]
    run_upgrade(url, "head", bootstrap_legacy=False)
    assert not check_schema_drift(url)
    with sqlite3.connect(path) as connection:
        assert connection.execute(
            "SELECT id,auto_discover_models,catalog_revision FROM model_sources ORDER BY id"
        ).fetchall() == [("empty", 1, 0), ("manual", 0, 0)]
    command.downgrade(config, parent)
    with sqlite3.connect(path) as connection:
        assert "auto_discover_models" not in {row[1] for row in connection.execute("PRAGMA table_info(model_sources)")}
        assert connection.execute("SELECT model FROM model_source_models").fetchall() == [("fixed",)]
    run_upgrade(url, "head", bootstrap_legacy=False)
    assert not check_schema_drift(url)
