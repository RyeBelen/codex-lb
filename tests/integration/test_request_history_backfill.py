from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from app.modules.request_logs.history_backfill import backfill_request_history

pytestmark = pytest.mark.integration

_FACT_COLUMNS_DDL = """
    account_id TEXT,
    api_key_id TEXT,
    session_id TEXT,
    request_id TEXT NOT NULL,
    requested_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    model TEXT NOT NULL,
    reasoning_effort TEXT,
    service_tier TEXT,
    source TEXT,
    useragent_group TEXT,
    request_kind TEXT NOT NULL,
    status TEXT NOT NULL,
    error_code TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cached_input_tokens INTEGER,
    reasoning_tokens INTEGER,
    cost_usd REAL,
    latency_ms INTEGER,
    latency_first_token_ms INTEGER
"""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _create_source(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE alembic_version (version_num TEXT NOT NULL)")
        connection.execute("INSERT INTO alembic_version VALUES ('source-revision')")
        connection.execute(f"CREATE TABLE request_logs (id INTEGER PRIMARY KEY, {_FACT_COLUMNS_DDL})")
        connection.execute(
            """INSERT INTO request_logs (
                   id, account_id, api_key_id, session_id, request_id, requested_at,
                   model, request_kind, status, input_tokens, output_tokens, cost_usd
               ) VALUES (1, 'account-1', 'key-1', 'session-1', 'response-1',
                         '2026-06-12 00:00:00', 'gpt-test', 'normal', 'success', 10, 5, 0.25)"""
        )


def _create_target(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE accounts (id TEXT PRIMARY KEY)")
        connection.execute("INSERT INTO accounts VALUES ('account-1')")
        connection.execute("CREATE TABLE request_logs (id INTEGER PRIMARY KEY)")
        connection.execute(
            f"""CREATE TABLE request_log_historical_facts (
                    request_log_id INTEGER PRIMARY KEY,
                    {_FACT_COLUMNS_DDL}
                )"""
        )


def _database_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


def test_snapshot_backfill_is_verified_and_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    _create_source(source)
    _create_target(target)
    source_sha = _sha256(source)

    dry_run = backfill_request_history(
        database_url=_database_url(target),
        snapshot_path=source,
        expected_source_sha256=source_sha,
        expected_source_revision="source-revision",
        expected_candidate_count=1,
    )
    assert dry_run.dry_run is True
    assert dry_run.candidate_count == 1
    assert dry_run.inserted_count == 0

    applied = backfill_request_history(
        database_url=_database_url(target),
        snapshot_path=source,
        expected_source_sha256=source_sha,
        expected_source_revision="source-revision",
        expected_candidate_count=1,
        expected_candidate_id_sha256=dry_run.candidate_id_sha256,
        apply=True,
        batch_size=1,
    )
    assert applied.inserted_count == 1

    repeated = backfill_request_history(
        database_url=_database_url(target),
        snapshot_path=source,
        expected_source_sha256=source_sha,
        expected_source_revision="source-revision",
        expected_candidate_count=0,
    )
    assert repeated.candidate_count == 0
    with sqlite3.connect(target) as connection:
        row = connection.execute(
            "SELECT request_log_id, request_id, input_tokens, output_tokens FROM request_log_historical_facts"
        ).fetchone()
        assert row == (1, "response-1", 10, 5)
        assert connection.execute("SELECT count(*) FROM request_logs").fetchone()[0] == 0
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"


def test_snapshot_backfill_rejects_hash_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    _create_source(source)
    _create_target(target)

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        backfill_request_history(
            database_url=_database_url(target),
            snapshot_path=source,
            expected_source_sha256="0" * 64,
            expected_source_revision="source-revision",
            expected_candidate_count=1,
        )
