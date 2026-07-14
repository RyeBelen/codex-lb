from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime, timedelta, timezone
from typing import TypedDict
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.dialects.postgresql import dialect as postgresql_dialect
from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.crypto import TokenEncryptor
from app.db.models import (
    Account,
    AccountStatus,
    Base,
    RequestLog,
    RequestLogHistoricalFact,
    RequestLogLegacyDailyAggregate,
)
from app.modules.reports.repository import (
    MISSING_USERAGENT_GROUP,
    DailyReportRangeTooLargeError,
    ReportsRepository,
    _daily_speed_medians_stmt,
)

pytestmark = pytest.mark.unit


class _ReportFilters(TypedDict):
    account_ids: list[str]
    model: str
    useragent_group: str


@pytest.fixture
async def async_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _make_account(account_id: str, email: str) -> Account:
    encryptor = TokenEncryptor()
    return Account(
        id=account_id,
        email=email,
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt("access"),
        refresh_token_encrypted=encryptor.encrypt("refresh"),
        id_token_encrypted=encryptor.encrypt("id"),
        last_refresh=datetime.now(timezone.utc).replace(tzinfo=None),
        status=AccountStatus.ACTIVE,
        deactivation_reason=None,
    )


def _make_historical_fact(
    request_log_id: int,
    *,
    account_id: str | None,
    request_id: str,
    requested_at: datetime,
    model: str = "gpt-5.1",
    useragent_group: str | None = "opencode",
    request_kind: str = "normal",
    source: str | None = None,
    status: str = "success",
    error_code: str | None = None,
    input_tokens: int | None = 10,
    output_tokens: int | None = 4,
    cached_input_tokens: int | None = 2,
    reasoning_tokens: int | None = None,
    cost_usd: float | None = 0.25,
    latency_ms: int | None = 1100,
    latency_first_token_ms: int | None = 100,
) -> RequestLogHistoricalFact:
    return RequestLogHistoricalFact(
        request_log_id=request_log_id,
        account_id=account_id,
        api_key_id=None,
        session_id=None,
        request_id=request_id,
        requested_at=requested_at,
        deleted_at=None,
        model=model,
        reasoning_effort=None,
        service_tier=None,
        source=source,
        useragent_group=useragent_group,
        request_kind=request_kind,
        status=status,
        error_code=error_code,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        reasoning_tokens=reasoning_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        latency_first_token_ms=latency_first_token_ms,
    )


def _make_legacy_aggregate(
    aggregate_key: str,
    *,
    bucket_date: date,
    account_id: str | None,
    model: str = "gpt-5.1",
    useragent_group: str | None = "opencode",
    request_kind: str = "normal",
    source: str | None = None,
    status: str = "success",
    request_count: int = 3,
    error_count: int = 0,
    input_tokens: int = 30,
    output_tokens: int = 12,
    cached_input_tokens: int = 6,
    cost_usd: float = 0.75,
) -> RequestLogLegacyDailyAggregate:
    return RequestLogLegacyDailyAggregate(
        aggregate_key=aggregate_key,
        bucket_date=bucket_date,
        api_key_id=None,
        account_id=account_id,
        model=model,
        status=status,
        error_code=None,
        request_kind=request_kind,
        service_tier=None,
        requested_service_tier=None,
        actual_service_tier=None,
        transport="http",
        upstream_transport="http",
        source=source,
        useragent_group=useragent_group,
        plan_type="plus",
        is_deleted=False,
        request_count=request_count,
        error_count=error_count,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        effective_output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        reasoning_tokens=0,
        cost_usd=cost_usd,
        cost_microdollars=round(cost_usd * 1_000_000),
        account_request_count=request_count,
        account_input_tokens=input_tokens,
        account_output_tokens=output_tokens,
        account_cached_input_tokens=cached_input_tokens,
        account_cost_usd=cost_usd,
        latency_ms_sum=0,
        latency_ms_count=0,
        latency_first_token_ms_sum=0,
        latency_first_token_ms_count=0,
        source_snapshot_sha256="a" * 64,
        source_row_sha256="b" * 64,
    )


@pytest.mark.asyncio
async def test_aggregate_daily_rows_groups_in_sql_and_returns_only_buckets_with_data(
    async_session: AsyncSession,
) -> None:
    repo = ReportsRepository(async_session)
    timezone_info = timezone(timedelta(hours=8))

    async_session.add(_make_account("acc_reports_daily", "reports-daily@example.com"))
    async_session.add_all(
        [
            RequestLog(
                account_id="acc_reports_daily",
                request_id="report-daily-1",
                requested_at=datetime(2026, 6, 1, 16, 30, tzinfo=timezone.utc).replace(tzinfo=None),
                model="gpt-5.1",
                status="success",
                input_tokens=10,
                output_tokens=4,
                cached_input_tokens=2,
                cost_usd=0.25,
                latency_ms=1200,
                latency_first_token_ms=200,
            ),
            RequestLog(
                account_id=None,
                request_id="report-daily-2",
                requested_at=datetime(2026, 6, 3, 16, 30, tzinfo=timezone.utc).replace(tzinfo=None),
                model="gpt-5.1",
                status="error",
                input_tokens=5,
                output_tokens=1,
                cached_input_tokens=0,
                cost_usd=0.1,
                latency_ms=2600,
                latency_first_token_ms=600,
            ),
        ]
    )
    await async_session.commit()

    rows = await repo.aggregate_daily_rows(
        date(2026, 6, 2),
        date(2026, 6, 4),
        timezone_info,
    )

    assert [row.date for row in rows] == ["2026-06-02", "2026-06-04"]
    assert rows[0].requests == 1
    assert rows[0].input_tokens == 10
    assert rows[0].output_tokens == 4
    assert rows[0].cached_input_tokens == 2
    assert rows[0].cost_usd == 0.25
    assert rows[0].active_accounts == 1
    assert rows[0].error_count == 0
    assert rows[0].median_ttft_ms == 200
    assert rows[0].median_tps == 4

    assert rows[1].requests == 1
    assert rows[1].input_tokens == 5
    assert rows[1].output_tokens == 1
    assert rows[1].cached_input_tokens == 0
    assert rows[1].cost_usd == 0.1
    assert rows[1].active_accounts == 0
    assert rows[1].error_count == 1
    assert rows[1].median_ttft_ms == 600
    assert rows[1].median_tps == 0.5


@pytest.mark.asyncio
async def test_aggregate_daily_rows_calculates_sql_medians_for_odd_even_and_invalid_speed_samples(
    async_session: AsyncSession,
) -> None:
    repo = ReportsRepository(async_session)
    account_id = "acc_reports_speed_medians"
    async_session.add(_make_account(account_id, "reports-speed-medians@example.com"))
    async_session.add_all(
        [
            # Day one ignores missing TTFT and invalid TPS samples: TTFT [100, 200, 300], TPS [10].
            # Reasoning tokens are not used for the existing output TPS metric.
            RequestLog(
                account_id=account_id,
                request_id="report-speed-even-1",
                requested_at=datetime(2026, 6, 1, 9, 0),
                model="gpt-5.1",
                status="success",
                output_tokens=None,
                reasoning_tokens=10,
                latency_ms=1100,
                latency_first_token_ms=100,
            ),
            RequestLog(
                account_id=account_id,
                request_id="report-speed-even-2",
                requested_at=datetime(2026, 6, 1, 10, 0),
                model="gpt-5.1",
                status="success",
                output_tokens=12,
                reasoning_tokens=999,
                latency_ms=1500,
                latency_first_token_ms=300,
            ),
            RequestLog(
                account_id=account_id,
                request_id="report-speed-even-missing-ttft",
                requested_at=datetime(2026, 6, 1, 11, 0),
                model="gpt-5.1",
                status="success",
                output_tokens=None,
                reasoning_tokens=None,
                latency_ms=1500,
                latency_first_token_ms=None,
            ),
            RequestLog(
                account_id=account_id,
                request_id="report-speed-even-invalid-generation",
                requested_at=datetime(2026, 6, 1, 12, 0),
                model="gpt-5.1",
                status="success",
                output_tokens=9,
                latency_ms=200,
                latency_first_token_ms=200,
            ),
            # Day two ignores reasoning-only and zero-output rows for TPS: TTFT [100, 200, 300, 400], TPS [4, 20].
            RequestLog(
                account_id=account_id,
                request_id="report-speed-odd-1",
                requested_at=datetime(2026, 6, 2, 9, 0),
                model="gpt-5.1",
                status="success",
                output_tokens=20,
                latency_ms=1100,
                latency_first_token_ms=100,
            ),
            RequestLog(
                account_id=account_id,
                request_id="report-speed-odd-2",
                requested_at=datetime(2026, 6, 2, 10, 0),
                model="gpt-5.1",
                status="success",
                output_tokens=3,
                latency_ms=950,
                latency_first_token_ms=200,
            ),
            RequestLog(
                account_id=account_id,
                request_id="report-speed-odd-invalid-output",
                requested_at=datetime(2026, 6, 2, 11, 0),
                model="gpt-5.1",
                status="success",
                output_tokens=0,
                reasoning_tokens=50,
                latency_ms=700,
                latency_first_token_ms=300,
            ),
            RequestLog(
                account_id=account_id,
                request_id="report-speed-odd-reasoning-only",
                requested_at=datetime(2026, 6, 2, 12, 0),
                model="gpt-5.1",
                status="success",
                output_tokens=None,
                reasoning_tokens=40,
                latency_ms=800,
                latency_first_token_ms=400,
            ),
        ]
    )
    await async_session.commit()

    rows = await repo.aggregate_daily_rows(date(2026, 6, 1), date(2026, 6, 2), timezone.utc)

    assert [(row.date, row.median_ttft_ms, row.median_tps) for row in rows] == [
        ("2026-06-01", 200.0, 10.0),
        ("2026-06-02", 250.0, 12.0),
    ]


@pytest.mark.asyncio
async def test_mixed_raw_and_historical_facts_preserve_report_filters_distinct_counts_and_medians(
    async_session: AsyncSession,
) -> None:
    repo = ReportsRepository(async_session)
    account_one = "acc_reports_mixed_one"
    account_two = "acc_reports_mixed_two"
    async_session.add_all(
        [
            _make_account(account_one, "reports-mixed-one@example.com"),
            _make_account(account_two, "reports-mixed-two@example.com"),
            _make_historical_fact(
                101,
                account_id=account_one,
                request_id="mixed-odd-fact-one",
                requested_at=datetime(2026, 6, 1, 9, 0),
                latency_first_token_ms=100,
                latency_ms=1100,
                output_tokens=4,
            ),
            RequestLog(
                account_id=account_one,
                request_id="mixed-odd-raw",
                requested_at=datetime(2026, 6, 1, 10, 0),
                model="gpt-5.1",
                useragent_group="opencode",
                request_kind="normal",
                status="success",
                input_tokens=10,
                output_tokens=8,
                cached_input_tokens=2,
                cost_usd=0.25,
                latency_ms=1200,
                latency_first_token_ms=200,
            ),
            _make_historical_fact(
                102,
                account_id=account_two,
                request_id="mixed-odd-fact-two",
                requested_at=datetime(2026, 6, 1, 11, 0),
                status="error",
                error_code="upstream_error",
                latency_first_token_ms=300,
                latency_ms=1300,
                output_tokens=12,
            ),
            _make_historical_fact(
                103,
                account_id=account_one,
                request_id="mixed-even-fact-one",
                requested_at=datetime(2026, 6, 2, 9, 0),
                latency_first_token_ms=100,
                latency_ms=1100,
                output_tokens=4,
            ),
            RequestLog(
                account_id=account_one,
                request_id="mixed-even-raw-one",
                requested_at=datetime(2026, 6, 2, 10, 0),
                model="gpt-5.1",
                useragent_group="opencode",
                request_kind="normal",
                status="success",
                input_tokens=10,
                output_tokens=8,
                cached_input_tokens=2,
                cost_usd=0.25,
                latency_ms=1200,
                latency_first_token_ms=200,
            ),
            _make_historical_fact(
                104,
                account_id=account_two,
                request_id="mixed-even-fact-two",
                requested_at=datetime(2026, 6, 2, 11, 0),
                latency_first_token_ms=300,
                latency_ms=1300,
                output_tokens=12,
            ),
            RequestLog(
                account_id=account_two,
                request_id="mixed-even-raw-two",
                requested_at=datetime(2026, 6, 2, 12, 0),
                model="gpt-5.1",
                useragent_group="opencode",
                request_kind="normal",
                status="success",
                input_tokens=10,
                output_tokens=16,
                cached_input_tokens=2,
                cost_usd=0.25,
                latency_ms=1400,
                latency_first_token_ms=400,
            ),
            _make_historical_fact(
                105,
                account_id=account_one,
                request_id="mixed-filtered-warmup",
                requested_at=datetime(2026, 6, 1, 12, 0),
                request_kind="warmup",
                cost_usd=100.0,
            ),
            RequestLog(
                account_id=account_one,
                request_id="mixed-filtered-useragent",
                requested_at=datetime(2026, 6, 1, 13, 0),
                model="gpt-5.1",
                useragent_group="CodexCLI",
                request_kind="normal",
                status="success",
                input_tokens=100,
                output_tokens=100,
                cached_input_tokens=100,
                cost_usd=100.0,
            ),
        ]
    )
    await async_session.commit()

    filters: _ReportFilters = {
        "account_ids": [account_one, account_two],
        "model": "gpt-5.1",
        "useragent_group": "opencode",
    }
    daily = await repo.aggregate_daily_rows(
        date(2026, 6, 1),
        date(2026, 6, 2),
        timezone.utc,
        **filters,
    )
    summary = await repo.aggregate_summary(
        datetime(2026, 6, 1),
        datetime(2026, 6, 3),
        **filters,
    )
    by_model = await repo.aggregate_by_model(
        datetime(2026, 6, 1),
        datetime(2026, 6, 3),
        **filters,
    )
    by_account = await repo.aggregate_by_account(
        datetime(2026, 6, 1),
        datetime(2026, 6, 3),
        **filters,
    )
    by_useragent = await repo.aggregate_by_useragent(
        datetime(2026, 6, 1),
        datetime(2026, 6, 3),
        **filters,
    )
    active_accounts = await repo.count_active_accounts(
        datetime(2026, 6, 1),
        datetime(2026, 6, 3),
        **filters,
    )
    earliest = await repo.earliest_report_activity_at(**filters)

    assert [(row.date, row.requests, row.active_accounts, row.error_count) for row in daily] == [
        ("2026-06-01", 3, 2, 1),
        ("2026-06-02", 4, 2, 0),
    ]
    assert [(row.median_ttft_ms, row.median_tps) for row in daily] == [(200.0, 8.0), (250.0, 10.0)]
    assert summary.total_requests == 7
    assert summary.total_errors == 1
    assert summary.active_accounts == 2
    assert summary.total_cost_usd == 1.75
    assert [(row.model, row.request_count, row.cost_usd) for row in by_model] == [("gpt-5.1", 7, 1.75)]
    assert [(row.account_id, row.request_count, row.cost_usd) for row in by_account] == [
        (account_one, 4, 1.0),
        (account_two, 3, 0.75),
    ]
    assert [(row.useragent_group, row.request_count, row.cost_usd) for row in by_useragent] == [("opencode", 7, 1.75)]
    assert active_accounts == 2
    assert earliest == datetime(2026, 6, 1, 9, 0)


@pytest.mark.asyncio
async def test_aggregate_daily_rows_speed_medians_preserve_filters_and_timezone_buckets(
    async_session: AsyncSession,
) -> None:
    repo = ReportsRepository(async_session)
    async_session.add_all(
        [
            _make_account("acc_reports_speed_filter", "reports-speed-filter@example.com"),
            _make_account("acc_reports_speed_other", "reports-speed-other@example.com"),
            RequestLog(
                account_id="acc_reports_speed_filter",
                request_id="report-speed-filter-match",
                requested_at=datetime(2026, 6, 1, 7, 0),
                model="gpt-5.1",
                useragent_group="opencode",
                status="success",
                output_tokens=4,
                latency_ms=1100,
                latency_first_token_ms=100,
            ),
            RequestLog(
                account_id="acc_reports_speed_filter",
                request_id="report-speed-filter-before-local-day",
                requested_at=datetime(2026, 6, 1, 6, 59, 59),
                model="gpt-5.1",
                useragent_group="opencode",
                status="success",
                output_tokens=9,
                latency_ms=1000,
                latency_first_token_ms=900,
            ),
            RequestLog(
                account_id="acc_reports_speed_other",
                request_id="report-speed-filter-other-account",
                requested_at=datetime(2026, 6, 1, 7, 0),
                model="gpt-5.1",
                useragent_group="opencode",
                status="success",
                output_tokens=8,
                latency_ms=1000,
                latency_first_token_ms=800,
            ),
            RequestLog(
                account_id="acc_reports_speed_filter",
                request_id="report-speed-filter-other-model",
                requested_at=datetime(2026, 6, 1, 7, 0),
                model="gpt-5.2",
                useragent_group="opencode",
                status="success",
                output_tokens=7,
                latency_ms=1000,
                latency_first_token_ms=700,
            ),
            RequestLog(
                account_id="acc_reports_speed_filter",
                request_id="report-speed-filter-other-useragent",
                requested_at=datetime(2026, 6, 1, 7, 0),
                model="gpt-5.1",
                useragent_group="CodexCLI",
                status="success",
                output_tokens=6,
                latency_ms=1000,
                latency_first_token_ms=600,
            ),
        ]
    )
    await async_session.commit()

    rows = await repo.aggregate_daily_rows(
        date(2026, 6, 1),
        date(2026, 6, 1),
        ZoneInfo("America/Los_Angeles"),
        account_ids=["acc_reports_speed_filter"],
        model="gpt-5.1",
        useragent_group="opencode",
    )

    assert [(row.date, row.requests, row.median_ttft_ms, row.median_tps) for row in rows] == [
        ("2026-06-01", 1, 100.0, 4.0),
    ]


@pytest.mark.parametrize(
    ("timezone_name", "report_date", "day_start", "day_end"),
    [
        (
            "America/New_York",
            date(2026, 3, 8),
            datetime(2026, 3, 8, 5, 0),
            datetime(2026, 3, 9, 4, 0),
        ),
        (
            "Asia/Kathmandu",
            date(2026, 6, 1),
            datetime(2026, 5, 31, 18, 15),
            datetime(2026, 6, 1, 18, 15),
        ),
    ],
)
@pytest.mark.asyncio
async def test_mixed_history_uses_exact_dst_and_non_hour_local_day_boundaries(
    async_session: AsyncSession,
    timezone_name: str,
    report_date: date,
    day_start: datetime,
    day_end: datetime,
) -> None:
    repo = ReportsRepository(async_session)
    account_id = f"acc_reports_timezone_{timezone_name.replace('/', '_')}"
    async_session.add(_make_account(account_id, f"{timezone_name.replace('/', '-')}@example.com"))
    async_session.add_all(
        [
            _make_historical_fact(
                201,
                account_id=account_id,
                request_id="timezone-fact-at-start",
                requested_at=day_start,
            ),
            RequestLog(
                account_id=account_id,
                request_id="timezone-raw-before-end",
                requested_at=day_end - timedelta(microseconds=1),
                model="gpt-5.1",
                request_kind="normal",
                status="success",
                input_tokens=10,
                output_tokens=4,
                cached_input_tokens=2,
                cost_usd=0.25,
            ),
            _make_historical_fact(
                202,
                account_id=account_id,
                request_id="timezone-fact-before-start",
                requested_at=day_start - timedelta(microseconds=1),
            ),
            RequestLog(
                account_id=account_id,
                request_id="timezone-raw-at-end",
                requested_at=day_end,
                model="gpt-5.1",
                request_kind="normal",
                status="success",
                input_tokens=10,
                output_tokens=4,
                cached_input_tokens=2,
                cost_usd=0.25,
            ),
        ]
    )
    await async_session.commit()

    rows = await repo.aggregate_daily_rows(
        report_date,
        report_date,
        ZoneInfo(timezone_name),
    )

    assert [(row.date, row.requests, row.cost_usd) for row in rows] == [(report_date.isoformat(), 2, 0.5)]


@pytest.mark.asyncio
async def test_daily_speed_medians_stmt_returns_only_one_row_per_populated_day_at_high_cardinality(
    async_session: AsyncSession,
) -> None:
    day_ranges = [
        ("2026-06-01", datetime(2026, 6, 1), datetime(2026, 6, 2)),
        ("2026-06-02", datetime(2026, 6, 2), datetime(2026, 6, 3)),
    ]
    async_session.add_all(
        [
            RequestLog(
                request_id=f"report-speed-many-{day}-{sample}",
                requested_at=datetime(2026, 6, day, 12, sample % 60),
                model="gpt-5.1",
                status="success",
                output_tokens=sample + 1,
                latency_ms=1000 + sample,
                latency_first_token_ms=sample,
            )
            for day in (1, 2)
            for sample in range(512)
        ]
    )
    await async_session.commit()

    result = await async_session.execute(_daily_speed_medians_stmt(day_ranges, None, None, None))
    rows = result.all()

    assert [(row.report_date, row.median_ttft_ms, row.median_tps) for row in rows] == [
        ("2026-06-01", 255.5, 256.5),
        ("2026-06-02", 255.5, 256.5),
    ]
    assert len(rows) == len(day_ranges)


def test_daily_speed_medians_stmt_compiles_to_portable_window_sql() -> None:
    statement = _daily_speed_medians_stmt(
        [("2026-06-01", datetime(2026, 6, 1), datetime(2026, 6, 2))],
        None,
        None,
        None,
    )

    for dialect in (sqlite_dialect(), postgresql_dialect()):
        sql = str(statement.compile(dialect=dialect, compile_kwargs={"literal_binds": True})).lower()

        assert "row_number() over" in sql
        assert "count(*) over" in sql
        assert "group by daily_ttft_ranks.report_date" in sql
        assert "group by daily_tps_ranks.report_date" in sql
        assert "request_log_historical_facts" in sql
        assert "request_logs" in sql
        assert "union all" in sql
        assert "percentile_cont" not in sql


@pytest.mark.asyncio
async def test_aggregate_daily_rows_supports_ranges_longer_than_sqlite_compound_limit(
    async_session: AsyncSession,
) -> None:
    repo = ReportsRepository(async_session)
    timezone_info = timezone.utc
    start_date = date(2024, 1, 1)
    end_date = start_date + timedelta(days=500)

    async_session.add(_make_account("acc_reports_long_range", "reports-long-range@example.com"))
    async_session.add_all(
        [
            RequestLog(
                account_id="acc_reports_long_range",
                request_id="report-long-range-1",
                requested_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc).replace(tzinfo=None),
                model="gpt-5.1",
                status="success",
                input_tokens=10,
                output_tokens=4,
                cached_input_tokens=2,
                cost_usd=0.25,
            ),
            RequestLog(
                account_id="acc_reports_long_range",
                request_id="report-long-range-2",
                requested_at=datetime(2025, 5, 15, 12, 0, tzinfo=timezone.utc).replace(tzinfo=None),
                model="gpt-5.1",
                status="error",
                input_tokens=5,
                output_tokens=1,
                cached_input_tokens=0,
                cost_usd=0.1,
            ),
        ]
    )
    await async_session.commit()

    rows = await repo.aggregate_daily_rows(start_date, end_date, timezone_info)

    assert [row.date for row in rows] == ["2024-01-01", "2025-05-15"]
    assert rows[0].requests == 1
    assert rows[0].cost_usd == 0.25
    assert rows[1].requests == 1
    assert rows[1].cost_usd == 0.1


@pytest.mark.asyncio
async def test_aggregate_daily_rows_rejects_ranges_over_supported_window(
    async_session: AsyncSession,
) -> None:
    repo = ReportsRepository(async_session)

    with pytest.raises(DailyReportRangeTooLargeError, match="730 days or less"):
        await repo.aggregate_daily_rows(
            date(2024, 1, 1),
            date(2026, 1, 1),
            timezone.utc,
        )


@pytest.mark.asyncio
async def test_report_filters_apply_to_all_aggregates_including_earliest_activity(
    async_session: AsyncSession,
) -> None:
    repo = ReportsRepository(async_session)
    matched_at = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    filtered_out_at = datetime(2026, 5, 30, 9, 0, tzinfo=timezone.utc).replace(tzinfo=None)

    async_session.add(_make_account("acc_reports_filters", "reports-filters@example.com"))
    async_session.add_all(
        [
            RequestLog(
                account_id="acc_reports_filters",
                request_id="report-filter-match",
                requested_at=matched_at,
                model="gpt-5.1",
                useragent_group="opencode",
                status="success",
                input_tokens=10,
                output_tokens=4,
                cached_input_tokens=2,
                cost_usd=0.25,
            ),
            RequestLog(
                account_id="acc_reports_filters",
                request_id="report-filter-other-useragent",
                requested_at=filtered_out_at,
                model="gpt-5.1",
                useragent_group="CodexCLI",
                status="success",
                input_tokens=100,
                output_tokens=40,
                cached_input_tokens=20,
                cost_usd=2.5,
            ),
        ]
    )
    await async_session.commit()

    summary = await repo.aggregate_summary(
        datetime(2026, 6, 1, 0, 0),
        datetime(2026, 6, 2, 0, 0),
        useragent_group="opencode",
    )
    daily_rows = await repo.aggregate_daily_rows(
        date(2026, 6, 1),
        date(2026, 6, 1),
        timezone.utc,
        useragent_group="opencode",
    )
    by_model = await repo.aggregate_by_model(
        datetime(2026, 6, 1, 0, 0),
        datetime(2026, 6, 2, 0, 0),
        useragent_group="opencode",
    )
    by_account = await repo.aggregate_by_account(
        datetime(2026, 6, 1, 0, 0),
        datetime(2026, 6, 2, 0, 0),
        useragent_group="opencode",
    )
    earliest_activity_at = await repo.earliest_report_activity_at(useragent_group="opencode")

    assert summary.total_requests == 1
    assert summary.total_cost_usd == 0.25
    assert len(daily_rows) == 1
    assert daily_rows[0].requests == 1
    assert by_model[0].model == "gpt-5.1"
    assert by_model[0].cost_usd == 0.25
    assert by_model[0].request_count == 1
    assert by_account[0].account_id == "acc_reports_filters"
    assert by_account[0].request_count == 1
    assert earliest_activity_at == matched_at


@pytest.mark.asyncio
async def test_aggregate_by_useragent_separates_real_unknown_from_missing_groups(
    async_session: AsyncSession,
) -> None:
    repo = ReportsRepository(async_session)

    async_session.add(_make_account("acc_reports_useragents", "reports-useragents@example.com"))
    async_session.add_all(
        [
            RequestLog(
                account_id="acc_reports_useragents",
                request_id="report-useragent-opencode",
                requested_at=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc).replace(tzinfo=None),
                model="gpt-5.1",
                useragent_group="opencode",
                status="success",
                input_tokens=10,
                output_tokens=4,
                cached_input_tokens=0,
                cost_usd=0.5,
            ),
            RequestLog(
                account_id="acc_reports_useragents",
                request_id="report-useragent-codex",
                requested_at=datetime(2026, 6, 1, 13, 0, tzinfo=timezone.utc).replace(tzinfo=None),
                model="gpt-5.2",
                useragent_group="CodexCLI",
                status="success",
                input_tokens=9,
                output_tokens=3,
                cached_input_tokens=0,
                cost_usd=0.3,
            ),
            _make_historical_fact(
                301,
                account_id="acc_reports_useragents",
                request_id="report-useragent-real-unknown",
                requested_at=datetime(2026, 6, 1, 13, 30, tzinfo=timezone.utc).replace(tzinfo=None),
                model="gpt-5.0",
                useragent_group="Unknown",
                status="success",
                input_tokens=9,
                output_tokens=2,
                cached_input_tokens=0,
                cost_usd=0.4,
            ),
            RequestLog(
                account_id="acc_reports_useragents",
                request_id="report-useragent-blank",
                requested_at=datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc).replace(tzinfo=None),
                model="gpt-5.3",
                useragent_group="",
                status="success",
                input_tokens=8,
                output_tokens=2,
                cached_input_tokens=0,
                cost_usd=0.2,
            ),
            _make_historical_fact(
                302,
                account_id="acc_reports_useragents",
                request_id="report-useragent-null",
                requested_at=datetime(2026, 6, 1, 15, 0, tzinfo=timezone.utc).replace(tzinfo=None),
                model="gpt-5.4",
                useragent_group=None,
                status="success",
                input_tokens=7,
                output_tokens=1,
                cached_input_tokens=0,
                cost_usd=0.1,
            ),
        ]
    )
    await async_session.commit()

    rows = await repo.aggregate_by_useragent(
        datetime(2026, 6, 1, 0, 0),
        datetime(2026, 6, 2, 0, 0),
    )
    missing_rows = await repo.aggregate_by_useragent(
        datetime(2026, 6, 1, 0, 0),
        datetime(2026, 6, 2, 0, 0),
        useragent_group=MISSING_USERAGENT_GROUP,
    )
    unknown_rows = await repo.aggregate_by_useragent(
        datetime(2026, 6, 1, 0, 0),
        datetime(2026, 6, 2, 0, 0),
        useragent_group="Unknown",
    )

    assert [(row.useragent_group, row.cost_usd, row.request_count) for row in rows] == [
        ("opencode", 0.5, 1),
        ("Unknown", 0.4, 1),
        ("CodexCLI", 0.3, 1),
        ("Missing User-Agent", 0.1, 1),
    ]
    assert [(row.useragent_group, row.cost_usd, row.request_count) for row in missing_rows] == [
        ("Missing User-Agent", 0.1, 1)
    ]
    assert [(row.useragent_group, row.cost_usd, row.request_count) for row in unknown_rows] == [("Unknown", 0.4, 1)]


@pytest.mark.asyncio
async def test_legacy_utc_history_merges_additive_reports_without_double_counting_accounts(
    async_session: AsyncSession,
) -> None:
    repo = ReportsRepository(async_session)
    async_session.add(_make_account("acc_legacy_reports", "legacy-reports@example.com"))
    async_session.add_all(
        [
            _make_legacy_aggregate(
                "legacy-april",
                bucket_date=date(2026, 4, 24),
                account_id="acc_legacy_reports",
                request_count=3,
                input_tokens=30,
                output_tokens=12,
                cached_input_tokens=6,
                cost_usd=0.75,
            ),
            _make_historical_fact(
                9001,
                account_id="acc_legacy_reports",
                request_id="exact-june",
                requested_at=datetime(2026, 6, 12, 12, 0),
                input_tokens=10,
                output_tokens=4,
                cached_input_tokens=2,
                cost_usd=0.25,
            ),
        ]
    )
    await async_session.commit()

    exact_only = await repo.aggregate_summary(
        datetime(2026, 4, 24),
        datetime(2026, 6, 13),
    )
    combined = await repo.aggregate_summary(
        datetime(2026, 4, 24),
        datetime(2026, 6, 13),
        include_legacy=True,
    )

    assert exact_only.total_requests == 1
    assert combined.total_requests == 4
    assert combined.total_input_tokens == 40
    assert combined.total_output_tokens == 16
    assert combined.total_cached_tokens == 8
    assert combined.total_cost_usd == pytest.approx(1.0)
    assert combined.active_accounts == 1

    by_model = await repo.aggregate_by_model(
        datetime(2026, 4, 24),
        datetime(2026, 6, 13),
        include_legacy=True,
    )
    by_account = await repo.aggregate_by_account(
        datetime(2026, 4, 24),
        datetime(2026, 6, 13),
        include_legacy=True,
    )
    by_useragent = await repo.aggregate_by_useragent(
        datetime(2026, 4, 24),
        datetime(2026, 6, 13),
        include_legacy=True,
    )

    assert [(row.model, row.request_count, row.cost_usd) for row in by_model] == [("gpt-5.1", 4, 1.0)]
    assert [(row.account_id, row.request_count, row.cost_usd) for row in by_account] == [("acc_legacy_reports", 4, 1.0)]
    assert [(row.useragent_group, row.request_count, row.cost_usd) for row in by_useragent] == [("opencode", 4, 1.0)]


@pytest.mark.asyncio
async def test_legacy_daily_rows_are_explicitly_aggregate_only(
    async_session: AsyncSession,
) -> None:
    repo = ReportsRepository(async_session)
    async_session.add(_make_account("acc_legacy_daily", "legacy-daily@example.com"))
    async_session.add(
        _make_legacy_aggregate(
            "legacy-daily",
            bucket_date=date(2026, 4, 24),
            account_id="acc_legacy_daily",
        )
    )
    await async_session.commit()

    excluded = await repo.aggregate_daily_rows(
        date(2026, 4, 24),
        date(2026, 4, 24),
        timezone.utc,
    )
    included = await repo.aggregate_daily_rows(
        date(2026, 4, 24),
        date(2026, 4, 24),
        timezone.utc,
        include_legacy=True,
    )
    coverage = await repo.legacy_coverage()

    assert excluded == []
    assert len(included) == 1
    assert included[0].date == "2026-04-24"
    assert included[0].requests == 3
    assert included[0].history_resolution == "legacy_aggregate"
    assert included[0].median_ttft_ms is None
    assert included[0].median_tps is None
    assert coverage.start_date == date(2026, 4, 24)
    assert coverage.end_date == date(2026, 4, 24)
    assert coverage.aggregate_rows == 1
    assert coverage.request_count == 3


@pytest.mark.asyncio
async def test_legacy_report_filters_keep_warmups_and_blank_useragents_out(
    async_session: AsyncSession,
) -> None:
    repo = ReportsRepository(async_session)
    async_session.add(_make_account("acc_legacy_filters", "legacy-filters@example.com"))
    async_session.add_all(
        [
            _make_legacy_aggregate(
                "legacy-visible",
                bucket_date=date(2026, 4, 24),
                account_id="acc_legacy_filters",
                useragent_group=None,
            ),
            _make_legacy_aggregate(
                "legacy-warmup",
                bucket_date=date(2026, 4, 24),
                account_id="acc_legacy_filters",
                request_kind="warmup",
                source="limit_warmup",
                request_count=99,
            ),
            _make_legacy_aggregate(
                "legacy-blank-useragent",
                bucket_date=date(2026, 4, 24),
                account_id="acc_legacy_filters",
                useragent_group="",
                cost_usd=0.5,
            ),
        ]
    )
    await async_session.commit()

    summary = await repo.aggregate_summary(
        datetime(2026, 4, 24),
        datetime(2026, 4, 25),
        include_legacy=True,
    )
    missing_useragent = await repo.aggregate_by_useragent(
        datetime(2026, 4, 24),
        datetime(2026, 4, 25),
        useragent_group=MISSING_USERAGENT_GROUP,
        include_legacy=True,
    )

    assert summary.total_requests == 6
    assert [(row.useragent_group, row.request_count) for row in missing_useragent] == [(MISSING_USERAGENT_GROUP, 3)]
