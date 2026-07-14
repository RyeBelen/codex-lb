from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.core.config.settings import get_settings
from app.db.migrate import run_upgrade
from app.db.models import Base
from app.modules.request_logs.legacy_aggregate_import import (
    LegacyAggregateTotals,
    import_legacy_daily_aggregates,
)

pytestmark = pytest.mark.integration

_DATABASE_URL = get_settings().database_url
_SOURCE_REVISION = "source-revision"
_BUCKET_DATE = date(2026, 4, 24)
_TOTALS = LegacyAggregateTotals(
    request_count=3,
    error_count=1,
    input_tokens=30,
    output_tokens=15,
    effective_output_tokens=17,
    cached_input_tokens=4,
    reasoning_tokens=2,
    cost_microdollars=123_456,
)


def _database_url(path: Path) -> str:
    return f"sqlite+aiosqlite:///{path.as_posix()}"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregate_key() -> str:
    dimensions = {
        "bucket_date": _BUCKET_DATE.isoformat(),
        "api_key_id": "key-1",
        "account_id": "account-1",
        "model": "gpt-test",
        "status": "success",
        "error_code": None,
        "request_kind": "normal",
        "service_tier": "default",
        "requested_service_tier": None,
        "actual_service_tier": None,
        "transport": "http",
        "upstream_transport": "http",
        "source": None,
        "useragent_group": "Codex CLI",
        "plan_type": "team",
        "is_deleted": False,
    }
    payload = json.dumps(dimensions, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _aggregate_key_sha256() -> str:
    encoded = _aggregate_key().encode("ascii")
    return hashlib.sha256(struct.pack(">I", len(encoded)) + encoded).hexdigest()


def _create_source(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE alembic_version (version_num TEXT NOT NULL);
            CREATE TABLE request_log_daily_aggregates (
                id INTEGER PRIMARY KEY,
                aggregate_key TEXT NOT NULL UNIQUE,
                bucket_date DATE NOT NULL,
                api_key_id TEXT,
                account_id TEXT,
                model TEXT NOT NULL,
                status TEXT NOT NULL,
                error_code TEXT,
                request_kind TEXT NOT NULL,
                service_tier TEXT,
                requested_service_tier TEXT,
                actual_service_tier TEXT,
                transport TEXT,
                upstream_transport TEXT,
                source TEXT,
                useragent_group TEXT,
                plan_type TEXT,
                is_deleted BOOLEAN NOT NULL,
                request_count INTEGER NOT NULL,
                error_count INTEGER NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                effective_output_tokens INTEGER NOT NULL,
                cached_input_tokens INTEGER NOT NULL,
                reasoning_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                cost_microdollars INTEGER NOT NULL,
                account_request_count INTEGER NOT NULL,
                account_input_tokens INTEGER NOT NULL,
                account_output_tokens INTEGER NOT NULL,
                account_cached_input_tokens INTEGER NOT NULL,
                account_cost_usd REAL NOT NULL,
                latency_ms_sum INTEGER NOT NULL,
                latency_ms_count INTEGER NOT NULL,
                latency_first_token_ms_sum INTEGER NOT NULL,
                latency_first_token_ms_count INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            );
            """
        )
        connection.execute("INSERT INTO alembic_version VALUES (?)", (_SOURCE_REVISION,))
        connection.execute(
            """INSERT INTO request_log_daily_aggregates VALUES (
                   1, ?, ?, 'key-1', 'account-1', 'gpt-test', 'success', NULL,
                   'normal', 'default', NULL, NULL, 'http', 'http', NULL,
                   'Codex CLI', 'team', 0, 3, 1, 30, 15, 17, 4, 2, 0.123456,
                   123456, 3, 30, 17, 4, 0.123456, 300, 3, 90, 3,
                   '2026-07-14 00:00:00', '2026-07-14 00:00:00'
               )""",
            (_aggregate_key(), _BUCKET_DATE.isoformat()),
        )


def _create_target(path: Path) -> None:
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()


async def _run_import(source: Path, target: Path, *, apply: bool = False):
    return await import_legacy_daily_aggregates(
        database_url=_database_url(target),
        snapshot_path=source,
        expected_source_sha256=_sha256(source),
        expected_source_revision=_SOURCE_REVISION,
        expected_row_count=1,
        expected_aggregate_key_sha256=_aggregate_key_sha256(),
        expected_first_bucket_date=_BUCKET_DATE,
        expected_last_bucket_date=_BUCKET_DATE,
        expected_totals=_TOTALS,
        apply=apply,
    )


def test_migration_adds_forward_only_legacy_archive(tmp_path: Path) -> None:
    target = tmp_path / "migration.db"
    run_upgrade(_database_url(target), "head", bootstrap_legacy=False)

    with sqlite3.connect(target) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(request_log_legacy_daily_aggregates)")}
        indexes = {row[1] for row in connection.execute("PRAGMA index_list(request_log_legacy_daily_aggregates)")}
        assert {"aggregate_key", "bucket_date", "source_snapshot_sha256", "source_row_sha256"} <= columns
        assert "idx_legacy_request_aggregates_date" in indexes
        assert "idx_legacy_request_aggregates_account_date" in indexes
        assert "idx_legacy_request_aggregates_api_key_date" in indexes


@pytest.mark.asyncio
async def test_verified_import_is_dry_run_first_and_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    _create_source(source)
    _create_target(target)

    dry_run = await _run_import(source, target)
    assert dry_run.dry_run is True
    assert dry_run.candidate_count == 1
    assert dry_run.inserted_count == 0

    applied = await _run_import(source, target, apply=True)
    assert applied.candidate_count == 1
    assert applied.inserted_count == 1

    repeated = await _run_import(source, target)
    assert repeated.candidate_count == 0
    with sqlite3.connect(target) as connection:
        row = connection.execute(
            """SELECT aggregate_key, request_count, source_snapshot_sha256
               FROM request_log_legacy_daily_aggregates"""
        ).fetchone()
        assert row == (_aggregate_key(), 3, _sha256(source))
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"


@pytest.mark.asyncio
async def test_import_rejects_exact_history_date_overlap(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    _create_source(source)
    _create_target(target)
    with sqlite3.connect(target) as connection:
        connection.execute(
            """INSERT INTO request_logs (request_id, request_kind, requested_at, model, status)
               VALUES ('request-overlap', 'normal', '2026-04-24 12:00:00', 'gpt-test', 'success')"""
        )

    with pytest.raises(ValueError, match="overlap 1 exact raw/fact rows"):
        await _run_import(source, target, apply=True)
    with sqlite3.connect(target) as connection:
        assert connection.execute("SELECT count(*) FROM request_log_legacy_daily_aggregates").fetchone()[0] == 0


@pytest.mark.asyncio
async def test_import_rejects_measure_total_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    _create_source(source)
    _create_target(target)

    with pytest.raises(ValueError, match="legacy aggregate totals mismatch"):
        await import_legacy_daily_aggregates(
            database_url=_database_url(target),
            snapshot_path=source,
            expected_source_sha256=_sha256(source),
            expected_source_revision=_SOURCE_REVISION,
            expected_row_count=1,
            expected_aggregate_key_sha256=_aggregate_key_sha256(),
            expected_first_bucket_date=_BUCKET_DATE,
            expected_last_bucket_date=_BUCKET_DATE,
            expected_totals=LegacyAggregateTotals(
                request_count=4,
                error_count=1,
                input_tokens=30,
                output_tokens=15,
                effective_output_tokens=17,
                cached_input_tokens=4,
                reasoning_tokens=2,
                cost_microdollars=123_456,
            ),
        )


@pytest.mark.asyncio
async def test_import_rejects_recomputed_aggregate_key_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    _create_source(source)
    _create_target(target)
    with sqlite3.connect(source) as connection:
        connection.execute(
            "UPDATE request_log_daily_aggregates SET aggregate_key = ?",
            ("0" * 64,),
        )

    with pytest.raises(ValueError, match="legacy aggregate key mismatch"):
        await _run_import(source, target)


@pytest.mark.asyncio
@pytest.mark.skipif(not _DATABASE_URL.startswith("postgresql+"), reason="PostgreSQL test database is not configured")
async def test_verified_import_is_portable_to_postgresql(db_setup, tmp_path: Path) -> None:
    del db_setup
    source = tmp_path / "source.db"
    _create_source(source)

    applied = await import_legacy_daily_aggregates(
        database_url=_DATABASE_URL,
        snapshot_path=source,
        expected_source_sha256=_sha256(source),
        expected_source_revision=_SOURCE_REVISION,
        expected_row_count=1,
        expected_aggregate_key_sha256=_aggregate_key_sha256(),
        expected_first_bucket_date=_BUCKET_DATE,
        expected_last_bucket_date=_BUCKET_DATE,
        expected_totals=_TOTALS,
        apply=True,
    )
    assert applied.inserted_count == 1

    repeated = await import_legacy_daily_aggregates(
        database_url=_DATABASE_URL,
        snapshot_path=source,
        expected_source_sha256=_sha256(source),
        expected_source_revision=_SOURCE_REVISION,
        expected_row_count=1,
        expected_aggregate_key_sha256=_aggregate_key_sha256(),
        expected_first_bucket_date=_BUCKET_DATE,
        expected_last_bucket_date=_BUCKET_DATE,
        expected_totals=_TOTALS,
    )
    assert repeated.candidate_count == 0
