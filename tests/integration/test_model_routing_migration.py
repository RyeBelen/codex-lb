import sqlite3

import pytest
from alembic import command

from app.db.migrate import _build_alembic_config, check_schema_drift, run_upgrade

pytestmark = pytest.mark.integration


def test_model_routing_migration_preserves_data_and_roundtrips(tmp_path):
    path = tmp_path / "routing.db"
    url = f"sqlite+aiosqlite:///{path}"
    parent = "20260912_000000_add_account_api_key_access"
    run_upgrade(url, parent, bootstrap_legacy=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO accounts (id,email,plan_type,status,access_token_encrypted,refresh_token_encrypted,"
            "id_token_encrypted,last_refresh,codex_installation_id,api_key_access_restricted) "
            "VALUES ('a','test@example.com','pro','active',x'01',x'02',x'03',CURRENT_TIMESTAMP,'installation',1)"
        )
    run_upgrade(url, "head", bootstrap_legacy=False)
    assert not check_schema_drift(url)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        assert connection.execute("SELECT api_key_access_restricted FROM accounts").fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM model_account_policies").fetchone() == (0,)
        connection.execute("INSERT INTO model_account_policies VALUES ('gpt-6-astra')")
        connection.execute("INSERT INTO model_account_grants VALUES ('gpt-6-astra','a')")
        connection.execute("DELETE FROM accounts WHERE id='a'")
        assert connection.execute("SELECT count(*) FROM model_account_grants").fetchone() == (0,)
        assert connection.execute("SELECT model FROM model_account_policies").fetchone() == ("gpt-6-astra",)
    command.downgrade(_build_alembic_config(url), parent)
    run_upgrade(url, "head", bootstrap_legacy=False)
    assert not check_schema_drift(url)
