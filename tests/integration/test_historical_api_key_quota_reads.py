from __future__ import annotations

from datetime import datetime

import pytest

from app.db.models import (
    Account,
    AccountStatus,
    LimitType,
    RequestLog,
    RequestLogHistoricalFact,
)
from app.db.session import SessionLocal
from app.modules.api_keys.repository import ApiKeysRepository
from app.modules.quota_planner.repository import QuotaPlannerRepository

pytestmark = pytest.mark.integration


def _account(account_id: str) -> Account:
    return Account(
        id=account_id,
        email=f"{account_id}@example.com",
        plan_type="plus",
        access_token_encrypted=b"access",
        refresh_token_encrypted=b"refresh",
        id_token_encrypted=b"id",
        last_refresh=datetime(2026, 6, 1, 8, 0),
        status=AccountStatus.ACTIVE,
    )


@pytest.mark.asyncio
async def test_api_key_bounded_reads_combine_compact_history_and_raw_tail(db_setup) -> None:
    del db_setup
    account_id = "historical-api-key-account"
    key_id = "historical-api-key"
    since = datetime(2026, 6, 1, 9, 0)
    until = datetime(2026, 6, 1, 11, 0)

    async with SessionLocal() as session:
        session.add(_account(account_id))
        session.add_all(
            [
                RequestLogHistoricalFact(
                    request_log_id=900_001,
                    account_id=account_id,
                    api_key_id=key_id,
                    request_id="historical-api-key-fact",
                    requested_at=datetime(2026, 6, 1, 9, 5),
                    model="gpt-5.4",
                    request_kind="normal",
                    status="success",
                    input_tokens=20,
                    output_tokens=3,
                    cached_input_tokens=2,
                    reasoning_tokens=99,
                    cost_usd=0.0000019,
                ),
                RequestLogHistoricalFact(
                    request_log_id=900_002,
                    account_id=account_id,
                    api_key_id=key_id,
                    request_id="historical-api-key-warmup",
                    requested_at=datetime(2026, 6, 1, 9, 10),
                    model="gpt-5.4",
                    request_kind="warmup",
                    status="success",
                    input_tokens=1_000,
                    output_tokens=1_000,
                    cached_input_tokens=1_000,
                    cost_usd=1.0,
                ),
                RequestLog(
                    account_id=account_id,
                    api_key_id=key_id,
                    request_id="historical-api-key-raw",
                    requested_at=datetime(2026, 6, 1, 10, 5),
                    model="gpt-5.4",
                    request_kind="normal",
                    status="success",
                    input_tokens=10,
                    output_tokens=None,
                    cached_input_tokens=50,
                    reasoning_tokens=5,
                    cost_usd=0.0000029,
                ),
            ]
        )
        await session.commit()

        repository = ApiKeysRepository(session)

        assert (
            await repository.get_limit_usage_value(
                key_id,
                limit_type=LimitType.TOTAL_TOKENS,
                since=since,
                until=until,
                model_filter="gpt-5.4",
            )
            == 38
        )
        assert (
            await repository.get_limit_usage_value(
                key_id,
                limit_type=LimitType.COST_USD,
                since=since,
                until=until,
                model_filter=None,
            )
            == 3
        )

        trends = await repository.trends_by_key(key_id, since, until)
        assert [(bucket.total_tokens, bucket.total_cost_usd) for bucket in trends] == [
            (23, 0.000002),
            (15, 0.000003),
        ]

        usage = await repository.usage_7d(key_id, since, until)
        assert usage.total_requests == 2
        assert usage.total_tokens == 38
        assert usage.cached_input_tokens == 30
        assert usage.total_cost_usd == 0.000005
        assert len(usage.account_costs) == 1
        assert usage.account_costs[0].account_id == account_id
        assert usage.account_costs[0].cost_usd == 0.000005

        account_costs = await repository.usage_7d_by_account(key_id, since, until)
        assert len(account_costs) == 1
        assert account_costs[0].account_id == account_id
        assert account_costs[0].cost_usd == 0.000005


@pytest.mark.asyncio
async def test_quota_planner_reads_and_claim_budget_combine_history_with_raw_tail(db_setup) -> None:
    del db_setup
    since = datetime(2026, 6, 1, 10, 0)

    async with SessionLocal() as session:
        session.add_all(
            [
                RequestLogHistoricalFact(
                    request_log_id=910_001,
                    request_id="historical-quota-fact",
                    requested_at=datetime(2026, 6, 1, 10, 1),
                    model="gpt-5.4",
                    reasoning_effort="medium",
                    request_kind="warmup",
                    status="success",
                    input_tokens=8,
                    output_tokens=None,
                    cached_input_tokens=2,
                    reasoning_tokens=3,
                    cost_usd=0.15,
                ),
                RequestLogHistoricalFact(
                    request_log_id=910_002,
                    request_id="historical-quota-deleted-fact",
                    requested_at=datetime(2026, 6, 1, 10, 2),
                    deleted_at=datetime(2026, 6, 1, 10, 3),
                    model="gpt-5.4",
                    reasoning_effort="medium",
                    request_kind="warmup",
                    status="success",
                    cost_usd=10.0,
                ),
                RequestLog(
                    request_id="historical-quota-raw",
                    requested_at=datetime(2026, 6, 1, 10, 5),
                    model="gpt-5.4",
                    reasoning_effort="medium",
                    request_kind="warmup",
                    status="success",
                    input_tokens=12,
                    output_tokens=4,
                    cached_input_tokens=3,
                    cost_usd=0.25,
                ),
            ]
        )
        await session.commit()

        repository = QuotaPlannerRepository(session)

        assert await repository.warmup_cost_since(since) == pytest.approx(0.4)
        bins = await repository.aggregate_demand_bins(since=since)
        assert len(bins) == 1
        assert bins[0].request_count == 2
        assert bins[0].input_tokens == 20
        assert bins[0].cached_input_tokens == 5
        assert bins[0].output_tokens == 7
        assert bins[0].cost_usd == pytest.approx(0.4)

        decision = await repository.log_decision(
            mode="shadow",
            action="warmup",
            idempotency_key="historical-quota-claim",
            status="planned",
        )
        claimed = await repository.claim_warmup_decision(
            decision.id,
            since=since,
            max_warmups=1,
            max_credits=0.3,
        )
        assert claimed is None
