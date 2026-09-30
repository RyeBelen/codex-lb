"""Drive early redemption through the scheduler, real DB coordination and usage refresh."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.core.clients.rate_limit_reset_credits import ConsumeResetCreditResponse, ResetCreditItem, ResetCreditsResponse
from app.core.crypto import TokenEncryptor
from app.core.usage.models import UsagePayload
from app.core.usage.reset_credits_refresh_scheduler import refresh_reset_credits_for_accounts
from app.db.models import Account, ResetCreditRedeemRequest
from app.db.session import SessionLocal
from app.modules.rate_limit_reset_credits import api as redeem_api
from app.modules.rate_limit_reset_credits.store import RateLimitResetCreditsStore
from app.modules.usage import updater as usage_updater
from app.modules.usage.repository import UsageRepository
from tests.integration.test_reset_credits_replica_safety import _import_account

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize(("fresh_weekly", "reset_seconds"), [(100, 172800), (40, 172800), (None, 172800), (100, 86399)])
async def test_weekly_empty_scheduler_rechecks_usage_and_serializes_replicas(
    async_client, monkeypatch, fresh_weekly, reset_seconds
):
    account_id = await _import_account(async_client, email="weekly-reset@example.com", account_id="weekly-reset")
    reset_at = int(datetime.now(UTC).timestamp()) + 172800
    async with SessionLocal() as session:
        await UsageRepository(session).add_entry(
            account_id, 100, window="secondary", reset_at=reset_at, window_minutes=10080
        )
        account = await session.get(Account, account_id)
        assert account is not None
        account.auto_redeem_reset_credits_when_weekly_exhausted = True
        await session.commit()
        session.expunge(account)
    credit = ResetCreditItem(id="weekly-credit", status="available", expires_at=datetime.now(UTC) + timedelta(days=6))
    credits = ResetCreditsResponse(available_count=1, credits=[credit])
    consume = AsyncMock(
        return_value=ConsumeResetCreditResponse.model_validate(
            {"code": "reset", "windows_reset": 1, "credit": {"id": "weekly"}}
        )
    )
    fetch = AsyncMock(return_value=credits)
    weekly = (
        {}
        if fresh_weekly is None
        else {
            "secondary_window": {
                "used_percent": fresh_weekly,
                "reset_at": int(datetime.now(UTC).timestamp()) + reset_seconds,
                "limit_window_seconds": 604800,
            }
        }
    )
    # Keep an old 100% DB row even when the fresh response omits weekly data.
    monkeypatch.setattr(
        usage_updater, "fetch_usage", AsyncMock(return_value=UsagePayload.model_validate({"rate_limit": weekly}))
    )
    monkeypatch.setattr(redeem_api, "consume_reset_credit", consume)

    async def tick():
        await refresh_reset_credits_for_accounts(
            accounts=[account],
            encryptor=TokenEncryptor(),
            store=RateLimitResetCreditsStore(),
            fetch_fn=fetch,
        )

    await asyncio.gather(tick(), tick())
    assert consume.await_count == (1 if fresh_weekly == 100 and reset_seconds >= 86400 else 0)
    async with SessionLocal() as session:
        pins = (
            await session.scalars(
                select(ResetCreditRedeemRequest).where(ResetCreditRedeemRequest.account_id == account_id)
            )
        ).all()
    assert len(pins) == (1 if fresh_weekly == 100 and reset_seconds >= 86400 else 0)
    if pins:
        assert pins[0].credit_id == credit.id
        assert pins[0].redeem_request_id.startswith("auto-reset-credit:")
