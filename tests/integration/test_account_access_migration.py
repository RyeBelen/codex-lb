from __future__ import annotations

import sqlite3

import pytest
from alembic import command
from anyio import to_thread
from sqlalchemy import create_engine, text

from app.core.config.settings import get_settings
from app.db.migrate import (
    _build_alembic_config,
    _ensure_alembic_version_table_capacity,
    check_schema_drift,
    run_upgrade,
)
from app.db.migration_url import to_sync_database_url

pytestmark = pytest.mark.integration


def test_account_access_upgrade_preserves_data_and_roundtrips(tmp_path):
    path = tmp_path / "access.db"
    url = f"sqlite+aiosqlite:///{path}"
    parent = "20260908_000000_add_api_key_denied_models"
    run_upgrade(url, parent, bootstrap_legacy=True)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO accounts (id,email,plan_type,status,access_token_encrypted,refresh_token_encrypted,"
            "id_token_encrypted,last_refresh,codex_installation_id) "
            "VALUES ('a','test@example.com','plus','active',x'01',x'02',x'03',CURRENT_TIMESTAMP,'installation')"
        )
        connection.execute(
            "INSERT INTO api_keys (id,name,key_hash,key_prefix,is_active,account_assignment_scope_enabled) "
            "VALUES ('k','Key','hash','prefix',1,1)"
        )
        connection.execute("INSERT INTO api_key_accounts (api_key_id,account_id) VALUES ('k','a')")
    run_upgrade(url, "head", bootstrap_legacy=False)
    assert not check_schema_drift(url)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        assert connection.execute("SELECT api_key_access_restricted FROM accounts").fetchone() == (0,)
        assert connection.execute("SELECT account_assignment_scope_enabled FROM api_keys").fetchone() == (1,)
        assert connection.execute("SELECT api_key_id,account_id FROM api_key_accounts").fetchall() == [("k", "a")]
        connection.execute("UPDATE accounts SET api_key_access_restricted=1")
        connection.execute("INSERT INTO account_api_key_grants (account_id,api_key_id) VALUES ('a','k')")
    command.downgrade(_build_alembic_config(url), parent)
    with sqlite3.connect(path) as connection:
        assert "api_key_access_restricted" not in {row[1] for row in connection.execute("PRAGMA table_info(accounts)")}
        assert connection.execute("SELECT email FROM accounts").fetchone() == ("test@example.com",)
    run_upgrade(url, "head", bootstrap_legacy=False)
    assert not check_schema_drift(url)


@pytest.mark.asyncio
async def test_account_access_roundtrip_on_configured_database(db_setup):
    """Exercise the configured SQLite or PostgreSQL test database, never the service database."""
    url = get_settings().database_url
    parent = "20260908_000000_add_api_key_denied_models"

    def roundtrip():
        config = _build_alembic_config(url)
        _ensure_alembic_version_table_capacity(config)
        command.stamp(config, "head")
        command.downgrade(config, parent)
        engine = create_engine(to_sync_database_url(url))
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO accounts (id,email,plan_type,status,access_token_encrypted,"
                        "refresh_token_encrypted,"
                        "id_token_encrypted,last_refresh,codex_installation_id) "
                        "VALUES ('migration-account','test@example.com','plus','active',:token,:token,:token,"
                        "CURRENT_TIMESTAMP,'installation')"
                    ),
                    {"token": b"token"},
                )
                connection.execute(
                    text(
                        "INSERT INTO api_keys (id,name,key_hash,key_prefix,is_active,account_assignment_scope_enabled) "
                        "VALUES ('migration-key','Key','hash','prefix',true,true)"
                    )
                )
                connection.execute(
                    text(
                        "INSERT INTO api_key_accounts (api_key_id,account_id) "
                        "VALUES ('migration-key','migration-account')"
                    )
                )
            run_upgrade(url, "head", bootstrap_legacy=False)
            assert not check_schema_drift(url)
            with engine.begin() as connection:
                assert not connection.scalar(text("SELECT api_key_access_restricted FROM accounts"))
                assert connection.scalar(text("SELECT account_assignment_scope_enabled FROM api_keys"))
                assert connection.scalar(text("SELECT count(*) FROM api_key_accounts")) == 1
                connection.execute(text("UPDATE accounts SET api_key_access_restricted=true"))
                connection.execute(
                    text(
                        "INSERT INTO account_api_key_grants (account_id,api_key_id) "
                        "VALUES ('migration-account','migration-key')"
                    )
                )
            command.downgrade(config, parent)
            run_upgrade(url, "head", bootstrap_legacy=False)
            assert not check_schema_drift(url)
            with engine.connect() as connection:
                assert connection.scalar(text("SELECT count(*) FROM accounts")) == 1
                assert connection.scalar(text("SELECT count(*) FROM api_key_accounts")) == 1
                assert connection.scalar(text("SELECT count(*) FROM account_api_key_grants")) == 0
        finally:
            engine.dispose()

    await to_thread.run_sync(roundtrip)
