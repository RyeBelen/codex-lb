from __future__ import annotations

import hashlib
import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path

from app.db.sqlite_utils import sqlite_db_path_from_url
from app.modules.request_logs.history import FACT_INSERT_COLUMNS

DEFAULT_BATCH_SIZE = 10_000
_SOURCE_REQUIRED_COLUMNS = frozenset({"id", *FACT_INSERT_COLUMNS[1:]})


@dataclass(frozen=True, slots=True)
class HistoryBackfillResult:
    dry_run: bool
    source_sha256: str
    source_revision: str
    source_column_count: int
    candidate_count: int
    candidate_id_sha256: str
    first_request_log_id: int | None
    last_request_log_id: int | None
    first_requested_at: str | None
    last_requested_at: str | None
    inserted_count: int


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _id_sha256(ids: list[int]) -> str:
    digest = hashlib.sha256()
    for request_log_id in ids:
        digest.update(struct.pack(">Q", request_log_id))
    return digest.hexdigest()


def _sqlite_path(database_url: str) -> Path:
    path = sqlite_db_path_from_url(database_url)
    if path is None:
        raise ValueError("historical request backfill requires a SQLite target database")
    return path.resolve()


def backfill_request_history(
    *,
    database_url: str,
    snapshot_path: Path,
    expected_source_sha256: str,
    expected_source_revision: str,
    expected_candidate_count: int,
    expected_candidate_id_sha256: str | None = None,
    apply: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> HistoryBackfillResult:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    source_path = snapshot_path.expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"snapshot not found: {source_path}")
    source_sha256 = _sha256_file(source_path)
    if source_sha256 != expected_source_sha256.lower():
        raise ValueError(f"snapshot SHA-256 mismatch expected={expected_source_sha256.lower()} actual={source_sha256}")

    target_path = _sqlite_path(database_url)
    if source_path == target_path:
        raise ValueError("snapshot and target database must be different files")

    connection = sqlite3.connect(str(target_path), timeout=60.0, uri=True)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("ATTACH DATABASE ? AS source", (f"file:{source_path.as_posix()}?mode=ro",))
        source_integrity = connection.execute("PRAGMA source.quick_check").fetchone()
        if source_integrity is None or source_integrity[0] != "ok":
            raise ValueError(f"snapshot quick_check failed: {source_integrity!r}")
        source_revision_row = connection.execute("SELECT version_num FROM source.alembic_version").fetchone()
        source_revision = str(source_revision_row[0]) if source_revision_row else ""
        if source_revision != expected_source_revision:
            raise ValueError(
                f"snapshot revision mismatch expected={expected_source_revision} actual={source_revision or 'missing'}"
            )

        source_columns = {
            str(row[1]) for row in connection.execute("PRAGMA source.table_info(request_logs)").fetchall()
        }
        missing_columns = sorted(_SOURCE_REQUIRED_COLUMNS - source_columns)
        if missing_columns:
            raise ValueError(f"snapshot request_logs missing columns: {', '.join(missing_columns)}")
        target_tables = {
            str(row[0])
            for row in connection.execute("SELECT name FROM main.sqlite_master WHERE type='table'").fetchall()
        }
        if "request_log_historical_facts" not in target_tables:
            raise ValueError("target database is not migrated: request_log_historical_facts is missing")

        missing_account_count = int(
            connection.execute(
                """SELECT count(*)
                   FROM source.request_logs AS source_log
                   WHERE source_log.account_id IS NOT NULL
                     AND NOT EXISTS (
                         SELECT 1 FROM main.accounts AS account
                         WHERE account.id = source_log.account_id
                     )
                     AND NOT EXISTS (
                         SELECT 1 FROM main.request_logs AS raw
                         WHERE raw.id = source_log.id
                     )
                     AND NOT EXISTS (
                         SELECT 1 FROM main.request_log_historical_facts AS fact
                         WHERE fact.request_log_id = source_log.id
                     )"""
            ).fetchone()[0]
        )
        if missing_account_count:
            raise ValueError(f"snapshot candidates reference {missing_account_count} absent accounts")

        candidate_rows = connection.execute(
            """SELECT source_log.id, source_log.requested_at
               FROM source.request_logs AS source_log
               WHERE NOT EXISTS (
                   SELECT 1 FROM main.request_logs AS raw
                   WHERE raw.id = source_log.id
               )
                 AND NOT EXISTS (
                   SELECT 1 FROM main.request_log_historical_facts AS fact
                   WHERE fact.request_log_id = source_log.id
               )
               ORDER BY source_log.id"""
        ).fetchall()
        candidate_ids = [int(row[0]) for row in candidate_rows]
        candidate_count = len(candidate_ids)
        if candidate_count != expected_candidate_count:
            raise ValueError(
                f"snapshot candidate count mismatch expected={expected_candidate_count} actual={candidate_count}"
            )
        candidate_id_sha256 = _id_sha256(candidate_ids)
        if expected_candidate_id_sha256 and candidate_id_sha256 != expected_candidate_id_sha256.lower():
            raise ValueError(
                "snapshot candidate id checksum mismatch "
                f"expected={expected_candidate_id_sha256.lower()} actual={candidate_id_sha256}"
            )

        inserted_count = 0
        if apply:
            target_columns = ", ".join(FACT_INSERT_COLUMNS)
            source_columns_sql = ", ".join(
                "id" if column == "request_log_id" else column for column in FACT_INSERT_COLUMNS
            )
            for offset in range(0, candidate_count, batch_size):
                batch_ids = candidate_ids[offset : offset + batch_size]
                placeholders = ", ".join("?" for _ in batch_ids)
                connection.execute("BEGIN IMMEDIATE")
                try:
                    result = connection.execute(
                        f"""INSERT INTO main.request_log_historical_facts ({target_columns})
                            SELECT {source_columns_sql}
                            FROM source.request_logs
                            WHERE id IN ({placeholders})""",
                        batch_ids,
                    )
                    projected = int(
                        connection.execute(
                            f"""SELECT count(*) FROM main.request_log_historical_facts
                                WHERE request_log_id IN ({placeholders})""",
                            batch_ids,
                        ).fetchone()[0]
                    )
                    if result.rowcount != len(batch_ids) or projected != len(batch_ids):
                        raise RuntimeError(
                            "snapshot backfill parity failed "
                            f"selected={len(batch_ids)} inserted={result.rowcount} projected={projected}"
                        )
                    connection.commit()
                    inserted_count += result.rowcount
                except BaseException:
                    connection.rollback()
                    raise

        first_id = candidate_ids[0] if candidate_ids else None
        last_id = candidate_ids[-1] if candidate_ids else None
        first_requested_at = min((str(row[1]) for row in candidate_rows), default=None)
        last_requested_at = max((str(row[1]) for row in candidate_rows), default=None)
        return HistoryBackfillResult(
            dry_run=not apply,
            source_sha256=source_sha256,
            source_revision=source_revision,
            source_column_count=len(source_columns),
            candidate_count=candidate_count,
            candidate_id_sha256=candidate_id_sha256,
            first_request_log_id=first_id,
            last_request_log_id=last_id,
            first_requested_at=first_requested_at,
            last_requested_at=last_requested_at,
            inserted_count=inserted_count,
        )
    finally:
        connection.close()
