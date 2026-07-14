from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import String, cast, func, insert, inspect, select
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.db.models import RequestLog, RequestLogHistoricalFact, RequestLogLegacyDailyAggregate
from app.db.sqlite_utils import sqlite_db_path_from_url

DEFAULT_BATCH_SIZE = 10_000
_SOURCE_TABLE = "request_log_daily_aggregates"
_MEASURE_COLUMNS = (
    "request_count",
    "error_count",
    "input_tokens",
    "output_tokens",
    "effective_output_tokens",
    "cached_input_tokens",
    "reasoning_tokens",
    "cost_microdollars",
)
_DIMENSION_COLUMNS = (
    "bucket_date",
    "api_key_id",
    "account_id",
    "model",
    "status",
    "error_code",
    "request_kind",
    "service_tier",
    "requested_service_tier",
    "actual_service_tier",
    "transport",
    "upstream_transport",
    "source",
    "useragent_group",
    "plan_type",
    "is_deleted",
)
_ARCHIVE_COLUMNS = (
    "aggregate_key",
    *_DIMENSION_COLUMNS,
    *_MEASURE_COLUMNS,
    "cost_usd",
    "account_request_count",
    "account_input_tokens",
    "account_output_tokens",
    "account_cached_input_tokens",
    "account_cost_usd",
    "latency_ms_sum",
    "latency_ms_count",
    "latency_first_token_ms_sum",
    "latency_first_token_ms_count",
)
_SOURCE_REQUIRED_COLUMNS = frozenset({"id", *_ARCHIVE_COLUMNS, "created_at", "updated_at"})


@dataclass(frozen=True, slots=True)
class LegacyAggregateTotals:
    request_count: int
    error_count: int
    input_tokens: int
    output_tokens: int
    effective_output_tokens: int
    cached_input_tokens: int
    reasoning_tokens: int
    cost_microdollars: int


@dataclass(frozen=True, slots=True)
class LegacyAggregateImportResult:
    dry_run: bool
    source_sha256: str
    source_revision: str
    source_row_count: int
    aggregate_key_sha256: str
    first_bucket_date: date | None
    last_bucket_date: date | None
    totals: LegacyAggregateTotals
    candidate_count: int
    inserted_count: int


@dataclass(frozen=True, slots=True)
class _SourceRow:
    values: tuple[str | int | float | bool | date | None, ...]
    row_sha256: str

    @property
    def aggregate_key(self) -> str:
        return str(self.values[0])

    @property
    def bucket_date(self) -> date:
        value = self.values[1]
        if not isinstance(value, date):
            raise TypeError("legacy aggregate bucket_date is not a date")
        return value

    def insert_values(self, source_sha256: str) -> dict[str, str | int | float | bool | date | None]:
        values = dict(zip(_ARCHIVE_COLUMNS, self.values, strict=True))
        values["source_snapshot_sha256"] = source_sha256
        values["source_row_sha256"] = self.row_sha256
        return values


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _aggregate_key_sha256(keys: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for key in sorted(keys):
        encoded = key.encode("ascii")
        digest.update(struct.pack(">I", len(encoded)))
        digest.update(encoded)
    return digest.hexdigest()


def _row_sha256(values: Sequence[str | int | float | bool | date | None]) -> str:
    normalized = [value.isoformat() if isinstance(value, date) else value for value in values]
    payload = json.dumps(normalized, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _expected_aggregate_key(values: Sequence[str | int | float | bool | date | None]) -> str:
    dimensions = dict(zip(_DIMENSION_COLUMNS, values[1 : 1 + len(_DIMENSION_COLUMNS)], strict=True))
    bucket_date = dimensions["bucket_date"]
    if not isinstance(bucket_date, date):
        raise TypeError("legacy aggregate bucket_date is not a date")
    dimensions["bucket_date"] = bucket_date.isoformat()
    dimensions["is_deleted"] = bool(dimensions["is_deleted"])
    encoded = json.dumps(dimensions, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_source_rows(connection: sqlite3.Connection) -> list[_SourceRow]:
    selected_columns = ", ".join(_ARCHIVE_COLUMNS)
    raw_rows = connection.execute(f"SELECT {selected_columns} FROM {_SOURCE_TABLE} ORDER BY aggregate_key").fetchall()
    rows: list[_SourceRow] = []
    for raw_row in raw_rows:
        values = list(raw_row)
        values[1] = date.fromisoformat(str(values[1])[:10])
        values[16] = bool(values[16])
        typed_values = tuple(values)
        if str(typed_values[0]) != _expected_aggregate_key(typed_values):
            raise ValueError(f"legacy aggregate key mismatch: {typed_values[0]}")
        rows.append(_SourceRow(values=typed_values, row_sha256=_row_sha256(typed_values)))
    return rows


def _sum_totals(rows: Sequence[_SourceRow]) -> LegacyAggregateTotals:
    offsets = {name: _ARCHIVE_COLUMNS.index(name) for name in _MEASURE_COLUMNS}

    def total(name: str) -> int:
        values = [row.values[offsets[name]] for row in rows]
        if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
            raise ValueError(f"legacy aggregate measure {name} is not an integer")
        return sum(value for value in values if isinstance(value, int))

    return LegacyAggregateTotals(
        request_count=total("request_count"),
        error_count=total("error_count"),
        input_tokens=total("input_tokens"),
        output_tokens=total("output_tokens"),
        effective_output_tokens=total("effective_output_tokens"),
        cached_input_tokens=total("cached_input_tokens"),
        reasoning_tokens=total("reasoning_tokens"),
        cost_microdollars=total("cost_microdollars"),
    )


def _load_verified_source(
    *,
    snapshot_path: Path,
    expected_source_sha256: str,
    expected_source_revision: str,
    expected_row_count: int,
    expected_aggregate_key_sha256: str,
    expected_first_bucket_date: date,
    expected_last_bucket_date: date,
    expected_totals: LegacyAggregateTotals,
) -> tuple[str, list[_SourceRow], LegacyAggregateTotals]:
    source_path = snapshot_path.expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"snapshot not found: {source_path}")
    source_sha256 = _sha256_file(source_path)
    if source_sha256 != expected_source_sha256.lower():
        raise ValueError(f"snapshot SHA-256 mismatch expected={expected_source_sha256.lower()} actual={source_sha256}")

    with sqlite3.connect(f"file:{source_path.as_posix()}?mode=ro", uri=True) as connection:
        integrity = connection.execute("PRAGMA quick_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            raise ValueError(f"snapshot quick_check failed: {integrity!r}")
        revision_rows = connection.execute("SELECT version_num FROM alembic_version").fetchall()
        revisions = tuple(str(row[0]) for row in revision_rows)
        if revisions != (expected_source_revision,):
            raise ValueError(
                "snapshot revision mismatch "
                f"expected={expected_source_revision} actual={','.join(revisions) or 'missing'}"
            )
        columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({_SOURCE_TABLE})")}
        missing_columns = sorted(_SOURCE_REQUIRED_COLUMNS - columns)
        if missing_columns:
            raise ValueError(f"snapshot {_SOURCE_TABLE} missing columns: {', '.join(missing_columns)}")
        rows = _read_source_rows(connection)

    if len(rows) != expected_row_count:
        raise ValueError(f"legacy aggregate row count mismatch expected={expected_row_count} actual={len(rows)}")
    key_sha256 = _aggregate_key_sha256(row.aggregate_key for row in rows)
    if key_sha256 != expected_aggregate_key_sha256.lower():
        raise ValueError(
            "legacy aggregate key checksum mismatch "
            f"expected={expected_aggregate_key_sha256.lower()} actual={key_sha256}"
        )
    first_bucket = min((row.bucket_date for row in rows), default=None)
    last_bucket = max((row.bucket_date for row in rows), default=None)
    if (first_bucket, last_bucket) != (expected_first_bucket_date, expected_last_bucket_date):
        raise ValueError(
            "legacy aggregate date range mismatch "
            f"expected={expected_first_bucket_date}..{expected_last_bucket_date} "
            f"actual={first_bucket}..{last_bucket}"
        )
    totals = _sum_totals(rows)
    if totals != expected_totals:
        raise ValueError(f"legacy aggregate totals mismatch expected={expected_totals!r} actual={totals!r}")
    return source_sha256, rows, totals


def _async_database_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        return database_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


async def _assert_target_schema(connection: AsyncConnection) -> None:
    required = {
        RequestLog.__tablename__,
        RequestLogHistoricalFact.__tablename__,
        RequestLogLegacyDailyAggregate.__tablename__,
    }
    tables = await connection.run_sync(lambda sync_connection: set(inspect(sync_connection).get_table_names()))
    missing = sorted(required - tables)
    if missing:
        raise ValueError(f"target database is not migrated; missing tables: {', '.join(missing)}")


async def _assert_no_exact_history_overlap(connection: AsyncConnection, bucket_dates: Sequence[date]) -> None:
    date_strings = [value.isoformat() for value in sorted(set(bucket_dates))]
    raw_count = await connection.scalar(
        select(func.count())
        .select_from(RequestLog)
        .where(cast(func.date(RequestLog.requested_at), String).in_(date_strings))
    )
    fact_count = await connection.scalar(
        select(func.count())
        .select_from(RequestLogHistoricalFact)
        .where(cast(func.date(RequestLogHistoricalFact.requested_at), String).in_(date_strings))
    )
    overlap_count = int(raw_count or 0) + int(fact_count or 0)
    if overlap_count:
        raise ValueError(f"legacy aggregate buckets overlap {overlap_count} exact raw/fact rows")


async def _existing_row_hashes(connection: AsyncConnection, keys: Sequence[str], batch_size: int) -> dict[str, str]:
    existing: dict[str, str] = {}
    for offset in range(0, len(keys), batch_size):
        batch = keys[offset : offset + batch_size]
        result = await connection.execute(
            select(
                RequestLogLegacyDailyAggregate.aggregate_key,
                RequestLogLegacyDailyAggregate.source_row_sha256,
            ).where(RequestLogLegacyDailyAggregate.aggregate_key.in_(batch))
        )
        existing.update((str(key), str(row_hash)) for key, row_hash in result.all())
    return existing


async def import_legacy_daily_aggregates(
    *,
    database_url: str,
    snapshot_path: Path,
    expected_source_sha256: str,
    expected_source_revision: str,
    expected_row_count: int,
    expected_aggregate_key_sha256: str,
    expected_first_bucket_date: date,
    expected_last_bucket_date: date,
    expected_totals: LegacyAggregateTotals,
    apply: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> LegacyAggregateImportResult:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    target_path = sqlite_db_path_from_url(database_url)
    if target_path is not None and target_path.resolve() == snapshot_path.expanduser().resolve():
        raise ValueError("snapshot and target database must be different files")
    source_sha256, rows, totals = _load_verified_source(
        snapshot_path=snapshot_path,
        expected_source_sha256=expected_source_sha256,
        expected_source_revision=expected_source_revision,
        expected_row_count=expected_row_count,
        expected_aggregate_key_sha256=expected_aggregate_key_sha256,
        expected_first_bucket_date=expected_first_bucket_date,
        expected_last_bucket_date=expected_last_bucket_date,
        expected_totals=expected_totals,
    )

    engine = create_async_engine(_async_database_url(database_url))
    try:
        async with engine.connect() as connection:
            await _assert_target_schema(connection)
            await _assert_no_exact_history_overlap(connection, [row.bucket_date for row in rows])
            existing = await _existing_row_hashes(connection, [row.aggregate_key for row in rows], batch_size)
        mismatched = [
            row.aggregate_key
            for row in rows
            if row.aggregate_key in existing and existing[row.aggregate_key] != row.row_sha256
        ]
        if mismatched:
            raise ValueError(f"legacy aggregate target row checksum mismatch: {mismatched[0]}")
        candidates = [row for row in rows if row.aggregate_key not in existing]
        inserted_count = 0
        if apply:
            for offset in range(0, len(candidates), batch_size):
                batch = candidates[offset : offset + batch_size]
                async with engine.begin() as connection:
                    result = await connection.execute(
                        insert(RequestLogLegacyDailyAggregate),
                        [row.insert_values(source_sha256) for row in batch],
                    )
                    if result.rowcount != len(batch):
                        raise RuntimeError(
                            f"legacy aggregate insert parity failed selected={len(batch)} inserted={result.rowcount}"
                        )
                    inserted_count += result.rowcount
    finally:
        await engine.dispose()

    return LegacyAggregateImportResult(
        dry_run=not apply,
        source_sha256=source_sha256,
        source_revision=expected_source_revision,
        source_row_count=len(rows),
        aggregate_key_sha256=_aggregate_key_sha256(row.aggregate_key for row in rows),
        first_bucket_date=min((row.bucket_date for row in rows), default=None),
        last_bucket_date=max((row.bucket_date for row in rows), default=None),
        totals=totals,
        candidate_count=len(candidates),
        inserted_count=inserted_count,
    )
