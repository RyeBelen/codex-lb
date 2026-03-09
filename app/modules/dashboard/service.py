from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.core import usage as usage_core
from app.core.crypto import TokenEncryptor
from app.core.usage.types import UsageWindowRow
from app.core.utils.time import utcnow
from app.db.models import UsageHistory
from app.modules.accounts.mappers import build_account_summaries
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import (
    AdditionalQuotaResponse,
    AdditionalWindowResponse,
    DashboardOverviewResponse,
    DashboardUsageWindows,
    DepletionResponse,
)
from app.modules.usage.builders import (
    build_additional_usage_summary,
    build_trends_from_buckets,
    build_usage_summary_response,
    build_usage_window_response,
)
from app.modules.usage.depletion_service import (
    compute_aggregate_depletion,
    compute_depletion_for_account,
)


class DashboardService:
    def __init__(self, repo: DashboardRepository) -> None:
        self._repo = repo
        self._encryptor = TokenEncryptor()

    async def get_overview(self) -> DashboardOverviewResponse:
        now = utcnow()
        accounts = await self._repo.list_accounts()
        primary_usage = await self._repo.latest_usage_by_account("primary")
        secondary_usage = await self._repo.latest_usage_by_account("secondary")

        account_summaries = build_account_summaries(
            accounts=accounts,
            primary_usage=primary_usage,
            secondary_usage=secondary_usage,
            encryptor=self._encryptor,
            include_auth=False,
        )

        primary_rows_raw = _rows_from_latest(primary_usage)
        secondary_rows_raw = _rows_from_latest(secondary_usage)
        primary_rows, secondary_rows = usage_core.normalize_weekly_only_rows(
            primary_rows_raw,
            secondary_rows_raw,
        )

        secondary_minutes = usage_core.resolve_window_minutes("secondary", secondary_rows)

        # Use bucket aggregation instead of loading all logs
        bucket_since = now - timedelta(minutes=secondary_minutes) if secondary_minutes else now - timedelta(days=7)
        bucket_rows = await self._repo.aggregate_logs_by_bucket(bucket_since)
        trends, bucket_metrics, bucket_cost = build_trends_from_buckets(bucket_rows, bucket_since)

        summary = build_usage_summary_response(
            accounts=accounts,
            primary_rows=primary_rows,
            secondary_rows=secondary_rows,
            logs_secondary=[],
            metrics_override=bucket_metrics,
            cost_override=bucket_cost,
        )

        primary_window_minutes = usage_core.resolve_window_minutes("primary", primary_rows)

        windows = DashboardUsageWindows(
            primary=build_usage_window_response(
                window_key="primary",
                window_minutes=primary_window_minutes,
                usage_rows=primary_rows,
                accounts=accounts,
            ),
            secondary=build_usage_window_response(
                window_key="secondary",
                window_minutes=secondary_minutes,
                usage_rows=secondary_rows,
                accounts=accounts,
            ),
        )

        # Fetch additional usage data
        additional_quotas = await self._build_additional_quotas()

        # Compute depletion from primary usage history
        depletion_response = _build_depletion(primary_usage, now)

        return DashboardOverviewResponse(
            last_sync_at=_latest_recorded_at(primary_usage, secondary_usage),
            accounts=account_summaries,
            summary=summary,
            windows=windows,
            trends=trends,
            additional_quotas=additional_quotas,
            depletion=depletion_response,
        )

    async def _build_additional_quotas(self) -> list[AdditionalQuotaResponse]:
        """Fetch additional usage data and build quota responses."""
        repo = self._repo
        limit_names = await repo.list_additional_limit_names()

        additional_usage_data: dict[str, dict[str, dict[str, Any]]] = {}
        for limit_name in limit_names:
            additional_usage_data[limit_name] = {
                "primary": await repo.latest_additional_usage_by_account(limit_name, "primary"),
                "secondary": await repo.latest_additional_usage_by_account(limit_name, "secondary"),
            }

        additional_summaries = build_additional_usage_summary(additional_usage_data)

        return [
            AdditionalQuotaResponse(
                limit_name=s.limit_name,
                metered_feature=s.metered_feature,
                primary_window=AdditionalWindowResponse(
                    used_percent=s.primary_window.used_percent,
                    reset_at=s.primary_window.reset_at,
                    window_minutes=s.primary_window.window_minutes,
                )
                if s.primary_window
                else None,
                secondary_window=AdditionalWindowResponse(
                    used_percent=s.secondary_window.used_percent,
                    reset_at=s.secondary_window.reset_at,
                    window_minutes=s.secondary_window.window_minutes,
                )
                if s.secondary_window
                else None,
            )
            for s in additional_summaries
        ]


def _build_depletion(
    primary_usage: dict[str, UsageHistory],
    now,
) -> DepletionResponse | None:
    """Compute aggregate depletion from primary usage history.

    Each account's latest entry is passed to ``compute_depletion_for_account``.
    The function requires >=2 data points to compute a rate; with only
    ``latest_by_account`` data the result will typically be ``None`` until the
    EWMA state has accumulated across multiple dashboard refreshes.
    """
    per_account_metrics = []
    for account_id, entry in primary_usage.items():
        metrics = compute_depletion_for_account(
            account_id=account_id,
            limit_name="standard",
            window="primary",
            history=[entry],
            now=now,
        )
        per_account_metrics.append(metrics)

    aggregate = compute_aggregate_depletion(per_account_metrics)
    if aggregate is None:
        return None

    return DepletionResponse(
        risk=aggregate.risk,
        risk_level=aggregate.risk_level,
        burn_rate=aggregate.burn_rate,
        safe_usage_percent=aggregate.safe_usage_percent,
        projected_exhaustion_at=aggregate.projected_exhaustion_at,
        seconds_until_exhaustion=aggregate.seconds_until_exhaustion,
    )


def _rows_from_latest(latest: dict[str, UsageHistory]) -> list[UsageWindowRow]:
    return [
        UsageWindowRow(
            account_id=entry.account_id,
            used_percent=entry.used_percent,
            reset_at=entry.reset_at,
            window_minutes=entry.window_minutes,
            recorded_at=entry.recorded_at,
        )
        for entry in latest.values()
    ]


def _latest_recorded_at(
    primary_usage: dict[str, UsageHistory],
    secondary_usage: dict[str, UsageHistory],
):
    timestamps = [
        entry.recorded_at
        for entry in list(primary_usage.values()) + list(secondary_usage.values())
        if entry.recorded_at is not None
    ]
    return max(timestamps) if timestamps else None
