from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from itertools import batched
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, literal, or_, select, union, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Subquery

from app.db.models import Account, RequestLogLegacyDailyAggregate
from app.modules.request_logs.history import request_history_selectable

_INTERNAL_LIMIT_WARMUP_SOURCE = "limit_warmup"
_INTERNAL_WARMUP_REQUEST_KINDS = ("warmup", "limit_warmup")
_SQLITE_COMPOUND_SELECT_LIMIT = 500
MAX_DAILY_REPORT_DAYS = 730
UNKNOWN_USERAGENT_GROUP = "Unknown"
MISSING_USERAGENT_GROUP = "Missing User-Agent"


class DailyReportRangeTooLargeError(ValueError):
    pass


@dataclass(frozen=True)
class DailyReportAggregateRow:
    date: str
    requests: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    cost_usd: float
    active_accounts: int
    error_count: int
    median_ttft_ms: float | None
    median_tps: float | None
    history_resolution: Literal["exact", "legacy_aggregate"] = "exact"


@dataclass(frozen=True)
class LegacyReportCoverageRow:
    start_date: date | None
    end_date: date | None
    aggregate_rows: int
    request_count: int


@dataclass(frozen=True)
class SummaryAggregateRow:
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_cached_tokens: int
    total_requests: int
    total_errors: int
    active_accounts: int


@dataclass(frozen=True)
class ModelAggregateRow:
    model: str
    cost_usd: float
    request_count: int


@dataclass(frozen=True)
class AccountAggregateRow:
    account_id: str | None
    alias: str | None
    cost_usd: float
    request_count: int


@dataclass(frozen=True)
class UserAgentAggregateRow:
    useragent_group: str
    cost_usd: float
    request_count: int


class ReportsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def aggregate_daily_rows(
        self,
        start_date: date,
        end_date: date,
        timezone_info: ZoneInfo | timezone,
        account_ids: list[str] | None = None,
        model: str | None = None,
        useragent_group: str | None = None,
        include_legacy: bool = False,
    ) -> list[DailyReportAggregateRow]:
        window_days = (end_date - start_date).days + 1
        if window_days > MAX_DAILY_REPORT_DAYS:
            raise DailyReportRangeTooLargeError(f"report date range must be {MAX_DAILY_REPORT_DAYS} days or less")
        day_ranges = list(_daily_bucket_ranges(start_date, end_date, timezone_info))
        if not day_ranges:
            return []

        rows: list[DailyReportAggregateRow] = []
        # SQLite caps compound SELECTs at 500 terms, so long report ranges are
        # executed in chunks instead of building a single oversized UNION ALL.
        for day_ranges_batch in batched(day_ranges, _SQLITE_COMPOUND_SELECT_LIMIT):
            day_ranges_list = list(day_ranges_batch)
            speed_result = await self._session.execute(
                _daily_speed_medians_stmt(day_ranges_list, account_ids, model, useragent_group)
            )
            speed_values = {
                speed_row.report_date: (
                    float(speed_row.median_ttft_ms or 0.0),
                    float(speed_row.median_tps or 0.0),
                )
                for speed_row in speed_result.all()
            }

            result = await self._session.execute(_daily_rows_stmt(day_ranges_list, account_ids, model, useragent_group))
            rows.extend(
                DailyReportAggregateRow(
                    date=row.report_date,
                    requests=int(row.requests or 0),
                    input_tokens=int(row.input_tokens or 0),
                    output_tokens=int(row.output_tokens or 0),
                    cached_input_tokens=int(row.cached_input_tokens or 0),
                    cost_usd=float(row.cost_usd or 0.0),
                    active_accounts=int(row.active_accounts or 0),
                    error_count=int(row.error_count or 0),
                    median_ttft_ms=speed_values.get(row.report_date, (0.0, 0.0))[0],
                    median_tps=speed_values.get(row.report_date, (0.0, 0.0))[1],
                )
                for row in result.all()
            )
        if include_legacy:
            rows = _merge_daily_rows(
                [
                    *rows,
                    *(
                        await self._aggregate_legacy_daily_rows(
                            start_date,
                            end_date,
                            account_ids,
                            model,
                            useragent_group,
                        )
                    ),
                ]
            )
        return rows

    async def aggregate_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        account_ids: list[str] | None = None,
        model: str | None = None,
        useragent_group: str | None = None,
        include_legacy: bool = False,
    ) -> SummaryAggregateRow:
        history = request_history_selectable(name="report_summary_history")
        conditions = _report_conditions(history, start_date, end_date, account_ids, model, useragent_group)

        result = await self._session.execute(
            select(
                func.coalesce(func.sum(history.c.cost_usd), 0.0).label("total_cost_usd"),
                func.coalesce(func.sum(history.c.input_tokens), 0).label("total_input_tokens"),
                func.coalesce(func.sum(history.c.output_tokens), 0).label("total_output_tokens"),
                func.coalesce(func.sum(history.c.cached_input_tokens), 0).label("total_cached_tokens"),
                func.count().label("total_requests"),
                func.coalesce(
                    func.sum(case((history.c.status != "success", 1), else_=0)),
                    0,
                ).label("total_errors"),
                func.count(func.distinct(history.c.account_id)).label("active_accounts"),
            ).where(and_(*conditions))
        )
        row = result.one()
        exact = SummaryAggregateRow(
            total_cost_usd=float(row.total_cost_usd),
            total_input_tokens=int(row.total_input_tokens),
            total_output_tokens=int(row.total_output_tokens),
            total_cached_tokens=int(row.total_cached_tokens),
            total_requests=int(row.total_requests),
            total_errors=int(row.total_errors),
            active_accounts=int(row.active_accounts),
        )
        if not include_legacy:
            return exact
        legacy = await self._aggregate_legacy_summary(
            start_date,
            end_date,
            account_ids,
            model,
            useragent_group,
        )
        return SummaryAggregateRow(
            total_cost_usd=exact.total_cost_usd + legacy.total_cost_usd,
            total_input_tokens=exact.total_input_tokens + legacy.total_input_tokens,
            total_output_tokens=exact.total_output_tokens + legacy.total_output_tokens,
            total_cached_tokens=exact.total_cached_tokens + legacy.total_cached_tokens,
            total_requests=exact.total_requests + legacy.total_requests,
            total_errors=exact.total_errors + legacy.total_errors,
            active_accounts=await self._count_active_accounts_with_legacy(
                start_date,
                end_date,
                account_ids,
                model,
                useragent_group,
            ),
        )

    async def aggregate_by_model(
        self,
        start_date: datetime,
        end_date: datetime,
        account_ids: list[str] | None = None,
        model: str | None = None,
        useragent_group: str | None = None,
        include_legacy: bool = False,
    ) -> list[ModelAggregateRow]:
        history = request_history_selectable(name="report_model_history")
        conditions = [
            *_report_conditions(history, start_date, end_date, account_ids, model, useragent_group),
            history.c.model.is_not(None),
        ]

        stmt = (
            select(
                history.c.model,
                func.coalesce(func.sum(history.c.cost_usd), 0.0).label("cost_usd"),
                func.count().label("request_count"),
            )
            .where(and_(*conditions))
            .group_by(history.c.model)
            .order_by(func.coalesce(func.sum(history.c.cost_usd), 0.0).desc())
        )
        result = await self._session.execute(stmt)
        rows = [
            ModelAggregateRow(
                model=row.model,
                cost_usd=float(row.cost_usd),
                request_count=int(row.request_count),
            )
            for row in result.all()
        ]
        if include_legacy:
            rows.extend(
                await self._aggregate_legacy_by_model(
                    start_date,
                    end_date,
                    account_ids,
                    model,
                    useragent_group,
                )
            )
        return _merge_model_rows(rows)

    async def aggregate_by_account(
        self,
        start_date: datetime,
        end_date: datetime,
        account_ids: list[str] | None = None,
        model: str | None = None,
        useragent_group: str | None = None,
        include_legacy: bool = False,
    ) -> list[AccountAggregateRow]:
        history = request_history_selectable(name="report_account_history")
        conditions = _report_conditions(history, start_date, end_date, account_ids, model, useragent_group)

        stmt = (
            select(
                history.c.account_id,
                func.coalesce(func.sum(history.c.cost_usd), 0.0).label("cost_usd"),
                func.count().label("request_count"),
            )
            .where(and_(*conditions))
            .group_by(history.c.account_id)
            .order_by(func.coalesce(func.sum(history.c.cost_usd), 0.0).desc())
        )
        result = await self._session.execute(stmt)
        rows = [
            AccountAggregateRow(
                account_id=row.account_id,
                alias=None,
                cost_usd=float(row.cost_usd),
                request_count=int(row.request_count),
            )
            for row in result.all()
        ]
        if include_legacy:
            rows.extend(
                await self._aggregate_legacy_by_account(
                    start_date,
                    end_date,
                    account_ids,
                    model,
                    useragent_group,
                )
            )

        account_ids_found = [row.account_id for row in rows if row.account_id]
        alias_map: dict[str | None, str | None] = {}
        if account_ids_found:
            alias_result = await self._session.execute(
                select(Account.id, Account.alias).where(Account.id.in_(account_ids_found))
            )
            alias_map = {account_id: alias for account_id, alias in alias_result.all()}

        return _merge_account_rows(
            [
                AccountAggregateRow(
                    account_id=row.account_id,
                    alias=alias_map.get(row.account_id),
                    cost_usd=row.cost_usd,
                    request_count=row.request_count,
                )
                for row in rows
            ]
        )

    async def aggregate_by_useragent(
        self,
        start_date: datetime,
        end_date: datetime,
        account_ids: list[str] | None = None,
        model: str | None = None,
        useragent_group: str | None = None,
        include_legacy: bool = False,
    ) -> list[UserAgentAggregateRow]:
        history = request_history_selectable(name="report_useragent_history")
        useragent_group_bucket = _useragent_group_bucket_expr(history)
        conditions = [
            *_report_conditions(history, start_date, end_date, account_ids, model, useragent_group),
            or_(history.c.useragent_group.is_(None), func.trim(history.c.useragent_group) != ""),
        ]

        stmt = (
            select(
                useragent_group_bucket.label("useragent_group"),
                func.coalesce(func.sum(history.c.cost_usd), 0.0).label("cost_usd"),
                func.count().label("request_count"),
            )
            .where(and_(*conditions))
            .group_by(useragent_group_bucket)
            .order_by(func.coalesce(func.sum(history.c.cost_usd), 0.0).desc())
        )
        result = await self._session.execute(stmt)
        rows = [
            UserAgentAggregateRow(
                useragent_group=row.useragent_group,
                cost_usd=float(row.cost_usd),
                request_count=int(row.request_count),
            )
            for row in result.all()
        ]
        if include_legacy:
            rows.extend(
                await self._aggregate_legacy_by_useragent(
                    start_date,
                    end_date,
                    account_ids,
                    model,
                    useragent_group,
                )
            )
        return _merge_useragent_rows(rows)

    async def count_active_accounts(
        self,
        start_date: datetime,
        end_date: datetime,
        account_ids: list[str] | None = None,
        model: str | None = None,
        useragent_group: str | None = None,
        include_legacy: bool = False,
    ) -> int:
        history = request_history_selectable(name="report_active_accounts_history")
        conditions = [
            *_report_conditions(history, start_date, end_date, account_ids, model, useragent_group),
            history.c.account_id.is_not(None),
        ]

        result = await self._session.execute(
            select(func.count(func.distinct(history.c.account_id))).where(and_(*conditions))
        )
        exact = int(result.scalar_one() or 0)
        if not include_legacy:
            return exact
        return await self._count_active_accounts_with_legacy(
            start_date,
            end_date,
            account_ids,
            model,
            useragent_group,
        )

    async def earliest_report_activity_at(
        self,
        account_ids: list[str] | None = None,
        model: str | None = None,
        useragent_group: str | None = None,
        include_legacy: bool = False,
    ) -> datetime | None:
        history = request_history_selectable(name="report_earliest_history")
        conditions = [_normal_traffic_clause(history)]
        if account_ids:
            conditions.append(history.c.account_id.in_(account_ids))
        if model:
            conditions.append(history.c.model == model)
        useragent_group_clause = _useragent_group_filter_clause(history, useragent_group)
        if useragent_group_clause is not None:
            conditions.append(useragent_group_clause)

        result = await self._session.execute(select(func.min(history.c.requested_at)).where(and_(*conditions)))
        value = result.scalar_one_or_none()
        exact_value = value if isinstance(value, datetime) else None
        if not include_legacy:
            return exact_value
        legacy_conditions = _legacy_dimension_conditions(account_ids, model, useragent_group)
        legacy_result = await self._session.execute(
            select(func.min(RequestLogLegacyDailyAggregate.bucket_date)).where(and_(*legacy_conditions))
        )
        legacy_value = legacy_result.scalar_one_or_none()
        legacy_datetime = (
            datetime.combine(legacy_value, datetime.min.time()) if isinstance(legacy_value, date) else None
        )
        candidates = [candidate for candidate in (exact_value, legacy_datetime) if candidate is not None]
        return min(candidates) if candidates else None

    async def legacy_coverage(self) -> LegacyReportCoverageRow:
        result = await self._session.execute(
            select(
                func.min(RequestLogLegacyDailyAggregate.bucket_date),
                func.max(RequestLogLegacyDailyAggregate.bucket_date),
                func.count(),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.request_count), 0),
            )
        )
        row = result.one()
        return LegacyReportCoverageRow(
            start_date=row[0] if isinstance(row[0], date) else None,
            end_date=row[1] if isinstance(row[1], date) else None,
            aggregate_rows=int(row[2] or 0),
            request_count=int(row[3] or 0),
        )

    async def _aggregate_legacy_daily_rows(
        self,
        start_date: date,
        end_date: date,
        account_ids: list[str] | None,
        model: str | None,
        useragent_group: str | None,
    ) -> list[DailyReportAggregateRow]:
        conditions = _legacy_date_conditions(start_date, end_date, account_ids, model, useragent_group)
        result = await self._session.execute(
            select(
                RequestLogLegacyDailyAggregate.bucket_date,
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.request_count), 0).label("requests"),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.output_tokens), 0).label("output_tokens"),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.cached_input_tokens), 0).label(
                    "cached_input_tokens"
                ),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.cost_usd), 0.0).label("cost_usd"),
                func.count(func.distinct(RequestLogLegacyDailyAggregate.account_id)).label("active_accounts"),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.error_count), 0).label("error_count"),
            )
            .where(and_(*conditions))
            .group_by(RequestLogLegacyDailyAggregate.bucket_date)
            .order_by(RequestLogLegacyDailyAggregate.bucket_date)
        )
        return [
            DailyReportAggregateRow(
                date=row.bucket_date.isoformat(),
                requests=int(row.requests or 0),
                input_tokens=int(row.input_tokens or 0),
                output_tokens=int(row.output_tokens or 0),
                cached_input_tokens=int(row.cached_input_tokens or 0),
                cost_usd=float(row.cost_usd or 0.0),
                active_accounts=int(row.active_accounts or 0),
                error_count=int(row.error_count or 0),
                median_ttft_ms=None,
                median_tps=None,
                history_resolution="legacy_aggregate",
            )
            for row in result.all()
        ]

    async def _aggregate_legacy_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        account_ids: list[str] | None,
        model: str | None,
        useragent_group: str | None,
    ) -> SummaryAggregateRow:
        conditions = _legacy_datetime_conditions(start_date, end_date, account_ids, model, useragent_group)
        result = await self._session.execute(
            select(
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.cost_usd), 0.0),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.input_tokens), 0),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.output_tokens), 0),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.cached_input_tokens), 0),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.request_count), 0),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.error_count), 0),
                func.count(func.distinct(RequestLogLegacyDailyAggregate.account_id)),
            ).where(and_(*conditions))
        )
        row = result.one()
        return SummaryAggregateRow(
            total_cost_usd=float(row[0] or 0.0),
            total_input_tokens=int(row[1] or 0),
            total_output_tokens=int(row[2] or 0),
            total_cached_tokens=int(row[3] or 0),
            total_requests=int(row[4] or 0),
            total_errors=int(row[5] or 0),
            active_accounts=int(row[6] or 0),
        )

    async def _aggregate_legacy_by_model(
        self,
        start_date: datetime,
        end_date: datetime,
        account_ids: list[str] | None,
        model: str | None,
        useragent_group: str | None,
    ) -> list[ModelAggregateRow]:
        conditions = _legacy_datetime_conditions(start_date, end_date, account_ids, model, useragent_group)
        result = await self._session.execute(
            select(
                RequestLogLegacyDailyAggregate.model,
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.cost_usd), 0.0).label("cost_usd"),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.request_count), 0).label("request_count"),
            )
            .where(and_(*conditions), RequestLogLegacyDailyAggregate.model.is_not(None))
            .group_by(RequestLogLegacyDailyAggregate.model)
        )
        return [
            ModelAggregateRow(row.model, float(row.cost_usd or 0.0), int(row.request_count or 0))
            for row in result.all()
        ]

    async def _aggregate_legacy_by_account(
        self,
        start_date: datetime,
        end_date: datetime,
        account_ids: list[str] | None,
        model: str | None,
        useragent_group: str | None,
    ) -> list[AccountAggregateRow]:
        conditions = _legacy_datetime_conditions(start_date, end_date, account_ids, model, useragent_group)
        result = await self._session.execute(
            select(
                RequestLogLegacyDailyAggregate.account_id,
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.cost_usd), 0.0).label("cost_usd"),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.request_count), 0).label("request_count"),
            )
            .where(and_(*conditions))
            .group_by(RequestLogLegacyDailyAggregate.account_id)
        )
        return [
            AccountAggregateRow(row.account_id, None, float(row.cost_usd or 0.0), int(row.request_count or 0))
            for row in result.all()
        ]

    async def _aggregate_legacy_by_useragent(
        self,
        start_date: datetime,
        end_date: datetime,
        account_ids: list[str] | None,
        model: str | None,
        useragent_group: str | None,
    ) -> list[UserAgentAggregateRow]:
        conditions = _legacy_datetime_conditions(start_date, end_date, account_ids, model, useragent_group)
        bucket = _legacy_useragent_group_bucket_expr()
        result = await self._session.execute(
            select(
                bucket.label("useragent_group"),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.cost_usd), 0.0).label("cost_usd"),
                func.coalesce(func.sum(RequestLogLegacyDailyAggregate.request_count), 0).label("request_count"),
            )
            .where(
                and_(*conditions),
                or_(
                    RequestLogLegacyDailyAggregate.useragent_group.is_(None),
                    func.trim(RequestLogLegacyDailyAggregate.useragent_group) != "",
                ),
            )
            .group_by(bucket)
        )
        return [
            UserAgentAggregateRow(row.useragent_group, float(row.cost_usd or 0.0), int(row.request_count or 0))
            for row in result.all()
        ]

    async def _count_active_accounts_with_legacy(
        self,
        start_date: datetime,
        end_date: datetime,
        account_ids: list[str] | None,
        model: str | None,
        useragent_group: str | None,
    ) -> int:
        history = request_history_selectable(name="report_active_accounts_combined_history")
        exact_conditions = [
            *_report_conditions(history, start_date, end_date, account_ids, model, useragent_group),
            history.c.account_id.is_not(None),
        ]
        legacy_conditions = [
            *_legacy_datetime_conditions(start_date, end_date, account_ids, model, useragent_group),
            RequestLogLegacyDailyAggregate.account_id.is_not(None),
        ]
        account_ids_union = union(
            select(history.c.account_id.label("account_id")).where(and_(*exact_conditions)),
            select(RequestLogLegacyDailyAggregate.account_id.label("account_id")).where(and_(*legacy_conditions)),
        ).subquery()
        result = await self._session.execute(select(func.count()).select_from(account_ids_union))
        return int(result.scalar_one() or 0)


def _report_conditions(
    history: Subquery,
    start_date: datetime,
    end_date: datetime,
    account_ids: list[str] | None,
    model: str | None,
    useragent_group: str | None,
) -> list:
    conditions = [
        history.c.requested_at >= start_date,
        history.c.requested_at < end_date,
        _normal_traffic_clause(history),
    ]
    if account_ids:
        conditions.append(history.c.account_id.in_(account_ids))
    if model:
        conditions.append(history.c.model == model)
    useragent_group_clause = _useragent_group_filter_clause(history, useragent_group)
    if useragent_group_clause is not None:
        conditions.append(useragent_group_clause)
    return conditions


def _useragent_group_bucket_expr(history: Subquery):
    return case(
        (history.c.useragent_group.is_(None), literal(MISSING_USERAGENT_GROUP)),
        else_=history.c.useragent_group,
    )


def _useragent_group_filter_clause(history: Subquery, useragent_group: str | None):
    if not useragent_group:
        return None
    if useragent_group == MISSING_USERAGENT_GROUP:
        return history.c.useragent_group.is_(None)
    return history.c.useragent_group == useragent_group


def _normal_traffic_clause(history: Subquery):
    return and_(
        or_(history.c.source.is_(None), history.c.source != _INTERNAL_LIMIT_WARMUP_SOURCE),
        or_(
            history.c.request_kind.is_(None),
            history.c.request_kind.not_in(_INTERNAL_WARMUP_REQUEST_KINDS),
        ),
    )


def _legacy_useragent_group_bucket_expr():
    return case(
        (RequestLogLegacyDailyAggregate.useragent_group.is_(None), literal(MISSING_USERAGENT_GROUP)),
        else_=RequestLogLegacyDailyAggregate.useragent_group,
    )


def _legacy_useragent_group_filter_clause(useragent_group: str | None):
    if not useragent_group:
        return None
    if useragent_group == MISSING_USERAGENT_GROUP:
        return RequestLogLegacyDailyAggregate.useragent_group.is_(None)
    return RequestLogLegacyDailyAggregate.useragent_group == useragent_group


def _normal_legacy_traffic_clause():
    return and_(
        or_(
            RequestLogLegacyDailyAggregate.source.is_(None),
            RequestLogLegacyDailyAggregate.source != _INTERNAL_LIMIT_WARMUP_SOURCE,
        ),
        or_(
            RequestLogLegacyDailyAggregate.request_kind.is_(None),
            RequestLogLegacyDailyAggregate.request_kind.not_in(_INTERNAL_WARMUP_REQUEST_KINDS),
        ),
    )


def _legacy_dimension_conditions(
    account_ids: list[str] | None,
    model: str | None,
    useragent_group: str | None,
) -> list:
    conditions = [_normal_legacy_traffic_clause()]
    if account_ids:
        conditions.append(RequestLogLegacyDailyAggregate.account_id.in_(account_ids))
    if model:
        conditions.append(RequestLogLegacyDailyAggregate.model == model)
    useragent_group_clause = _legacy_useragent_group_filter_clause(useragent_group)
    if useragent_group_clause is not None:
        conditions.append(useragent_group_clause)
    return conditions


def _legacy_date_conditions(
    start_date: date,
    end_date: date,
    account_ids: list[str] | None,
    model: str | None,
    useragent_group: str | None,
) -> list:
    return [
        RequestLogLegacyDailyAggregate.bucket_date >= start_date,
        RequestLogLegacyDailyAggregate.bucket_date <= end_date,
        *_legacy_dimension_conditions(account_ids, model, useragent_group),
    ]


def _legacy_datetime_conditions(
    start_date: datetime,
    end_date: datetime,
    account_ids: list[str] | None,
    model: str | None,
    useragent_group: str | None,
) -> list:
    return [
        RequestLogLegacyDailyAggregate.bucket_date >= start_date.date(),
        RequestLogLegacyDailyAggregate.bucket_date < end_date.date(),
        *_legacy_dimension_conditions(account_ids, model, useragent_group),
    ]


def _merge_daily_rows(rows: list[DailyReportAggregateRow]) -> list[DailyReportAggregateRow]:
    merged: dict[str, DailyReportAggregateRow] = {}
    for row in rows:
        existing = merged.get(row.date)
        if existing is None:
            merged[row.date] = row
            continue
        has_legacy = "legacy_aggregate" in (existing.history_resolution, row.history_resolution)
        merged[row.date] = DailyReportAggregateRow(
            date=row.date,
            requests=existing.requests + row.requests,
            input_tokens=existing.input_tokens + row.input_tokens,
            output_tokens=existing.output_tokens + row.output_tokens,
            cached_input_tokens=existing.cached_input_tokens + row.cached_input_tokens,
            cost_usd=existing.cost_usd + row.cost_usd,
            active_accounts=existing.active_accounts + row.active_accounts,
            error_count=existing.error_count + row.error_count,
            median_ttft_ms=None if has_legacy else existing.median_ttft_ms,
            median_tps=None if has_legacy else existing.median_tps,
            history_resolution="legacy_aggregate" if has_legacy else "exact",
        )
    return [merged[key] for key in sorted(merged)]


def _merge_model_rows(rows: list[ModelAggregateRow]) -> list[ModelAggregateRow]:
    merged: dict[str, ModelAggregateRow] = {}
    for row in rows:
        existing = merged.get(row.model)
        merged[row.model] = ModelAggregateRow(
            model=row.model,
            cost_usd=row.cost_usd + (existing.cost_usd if existing else 0.0),
            request_count=row.request_count + (existing.request_count if existing else 0),
        )
    return sorted(merged.values(), key=lambda row: row.cost_usd, reverse=True)


def _merge_account_rows(rows: list[AccountAggregateRow]) -> list[AccountAggregateRow]:
    merged: dict[str | None, AccountAggregateRow] = {}
    for row in rows:
        existing = merged.get(row.account_id)
        merged[row.account_id] = AccountAggregateRow(
            account_id=row.account_id,
            alias=row.alias or (existing.alias if existing else None),
            cost_usd=row.cost_usd + (existing.cost_usd if existing else 0.0),
            request_count=row.request_count + (existing.request_count if existing else 0),
        )
    return sorted(merged.values(), key=lambda row: row.cost_usd, reverse=True)


def _merge_useragent_rows(rows: list[UserAgentAggregateRow]) -> list[UserAgentAggregateRow]:
    merged: dict[str, UserAgentAggregateRow] = {}
    for row in rows:
        existing = merged.get(row.useragent_group)
        merged[row.useragent_group] = UserAgentAggregateRow(
            useragent_group=row.useragent_group,
            cost_usd=row.cost_usd + (existing.cost_usd if existing else 0.0),
            request_count=row.request_count + (existing.request_count if existing else 0),
        )
    return sorted(merged.values(), key=lambda row: row.cost_usd, reverse=True)


def _day_ranges_cte(day_ranges: list[tuple[str, datetime, datetime]]):
    day_range_rows = [
        select(
            literal(report_date).label("report_date"),
            literal(day_start).label("day_start"),
            literal(day_end).label("day_end"),
        )
        for report_date, day_start, day_end in day_ranges
    ]
    day_ranges_query = day_range_rows[0] if len(day_range_rows) == 1 else union_all(*day_range_rows)
    return day_ranges_query.cte("report_days")


def _daily_speed_medians_stmt(
    day_ranges: list[tuple[str, datetime, datetime]],
    account_ids: list[str] | None,
    model: str | None,
    useragent_group: str | None,
):
    history = request_history_selectable(name="report_daily_speed_history")
    useragent_group_clause = _useragent_group_filter_clause(history, useragent_group)
    day_ranges_cte = _day_ranges_cte(day_ranges)
    traffic_join = day_ranges_cte.join(
        history,
        and_(
            history.c.requested_at >= day_ranges_cte.c.day_start,
            history.c.requested_at < day_ranges_cte.c.day_end,
            _normal_traffic_clause(history),
            *([history.c.account_id.in_(account_ids)] if account_ids else []),
            *([history.c.model == model] if model else []),
            *([useragent_group_clause] if useragent_group_clause is not None else []),
        ),
    )
    token_count = history.c.output_tokens
    ttft_values_cte = (
        select(
            day_ranges_cte.c.report_date,
            history.c.latency_first_token_ms.label("ttft_ms"),
        )
        .select_from(traffic_join)
        .where(history.c.latency_first_token_ms.is_not(None))
        .cte("daily_ttft_values")
    )
    tps_values_cte = (
        select(
            day_ranges_cte.c.report_date,
            (token_count * 1000.0 / (history.c.latency_ms - history.c.latency_first_token_ms)).label("tps"),
        )
        .select_from(traffic_join)
        .where(
            token_count.is_not(None),
            token_count > 0,
            history.c.latency_ms.is_not(None),
            history.c.latency_first_token_ms.is_not(None),
            history.c.latency_ms > history.c.latency_first_token_ms,
        )
        .cte("daily_tps_values")
    )
    ttft_count = func.count().over(partition_by=ttft_values_cte.c.report_date)
    ttft_ranked_cte = select(
        ttft_values_cte.c.report_date,
        ttft_values_cte.c.ttft_ms,
        ttft_count.label("sample_count"),
        func.row_number()
        .over(partition_by=ttft_values_cte.c.report_date, order_by=ttft_values_cte.c.ttft_ms)
        .label("ttft_rank"),
    ).cte("daily_ttft_ranks")
    tps_count = func.count().over(partition_by=tps_values_cte.c.report_date)
    tps_ranked_cte = select(
        tps_values_cte.c.report_date,
        tps_values_cte.c.tps,
        tps_count.label("sample_count"),
        func.row_number()
        .over(partition_by=tps_values_cte.c.report_date, order_by=tps_values_cte.c.tps)
        .label("tps_rank"),
    ).cte("daily_tps_ranks")

    # A median contains the one center row for odd samples and both center rows
    # for even samples. Multiplication avoids dialect-specific integer division.
    ttft_is_middle = and_(
        ttft_ranked_cte.c.ttft_rank * 2 >= ttft_ranked_cte.c.sample_count,
        ttft_ranked_cte.c.ttft_rank * 2 <= ttft_ranked_cte.c.sample_count + 2,
    )
    tps_is_middle = and_(
        tps_ranked_cte.c.tps_rank * 2 >= tps_ranked_cte.c.sample_count,
        tps_ranked_cte.c.tps_rank * 2 <= tps_ranked_cte.c.sample_count + 2,
    )
    ttft_medians_cte = (
        select(
            ttft_ranked_cte.c.report_date,
            func.avg(case((ttft_is_middle, ttft_ranked_cte.c.ttft_ms), else_=None)).label("median_ttft_ms"),
        )
        .group_by(ttft_ranked_cte.c.report_date)
        .cte("daily_ttft_medians")
    )
    tps_medians_cte = (
        select(
            tps_ranked_cte.c.report_date,
            func.avg(case((tps_is_middle, tps_ranked_cte.c.tps), else_=None)).label("median_tps"),
        )
        .group_by(tps_ranked_cte.c.report_date)
        .cte("daily_tps_medians")
    )
    return (
        select(
            day_ranges_cte.c.report_date,
            func.coalesce(ttft_medians_cte.c.median_ttft_ms, 0.0).label("median_ttft_ms"),
            func.coalesce(tps_medians_cte.c.median_tps, 0.0).label("median_tps"),
        )
        .select_from(
            day_ranges_cte.outerjoin(
                ttft_medians_cte,
                ttft_medians_cte.c.report_date == day_ranges_cte.c.report_date,
            ).outerjoin(
                tps_medians_cte,
                tps_medians_cte.c.report_date == day_ranges_cte.c.report_date,
            )
        )
        .order_by(day_ranges_cte.c.report_date)
    )


def _daily_rows_stmt(
    day_ranges: list[tuple[str, datetime, datetime]],
    account_ids: list[str] | None,
    model: str | None,
    useragent_group: str | None,
):
    history = request_history_selectable(name="report_daily_history")
    useragent_group_clause = _useragent_group_filter_clause(history, useragent_group)
    day_ranges_cte = _day_ranges_cte(day_ranges)
    return (
        select(
            day_ranges_cte.c.report_date,
            func.count(history.c.id).label("requests"),
            func.coalesce(func.sum(history.c.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(history.c.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(history.c.cached_input_tokens), 0).label("cached_input_tokens"),
            func.coalesce(func.sum(history.c.cost_usd), 0.0).label("cost_usd"),
            func.count(func.distinct(history.c.account_id)).label("active_accounts"),
            func.coalesce(
                func.sum(case((history.c.status != "success", 1), else_=0)),
                0,
            ).label("error_count"),
        )
        .select_from(
            day_ranges_cte.join(
                history,
                and_(
                    history.c.requested_at >= day_ranges_cte.c.day_start,
                    history.c.requested_at < day_ranges_cte.c.day_end,
                    _normal_traffic_clause(history),
                    *([history.c.account_id.in_(account_ids)] if account_ids else []),
                    *([history.c.model == model] if model else []),
                    *([useragent_group_clause] if useragent_group_clause is not None else []),
                ),
            )
        )
        .group_by(day_ranges_cte.c.report_date)
        .order_by(day_ranges_cte.c.report_date)
    )


def _daily_bucket_ranges(
    start_date: date,
    end_date: date,
    timezone_info: ZoneInfo | timezone,
) -> list[tuple[str, datetime, datetime]]:
    ranges: list[tuple[str, datetime, datetime]] = []
    current_date = start_date
    while current_date <= end_date:
        day_start = datetime.combine(current_date, datetime.min.time(), tzinfo=timezone_info)
        next_day_start = datetime.combine(current_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone_info)
        ranges.append(
            (
                current_date.isoformat(),
                day_start.astimezone(timezone.utc).replace(tzinfo=None),
                next_day_start.astimezone(timezone.utc).replace(tzinfo=None),
            )
        )
        current_date += timedelta(days=1)
    return ranges
