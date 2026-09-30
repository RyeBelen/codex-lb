from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import update

from app.core.auth import generate_unique_account_id
from app.core.utils.time import utcnow
from app.db.models import Account
from app.db.session import SessionLocal
from app.modules.accounts.service import AccountsService

pytestmark = pytest.mark.integration


def _encode_jwt(payload: Mapping[str, object]) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"header.{body}.sig"


def _auth_file(*, email: str, raw_account_id: str) -> dict[str, tuple[str, str, str]]:
    payload = {
        "email": email,
        "chatgpt_account_id": raw_account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": "plus"},
    }
    auth_json = {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": "access",
            "refreshToken": "refresh",
            "accountId": raw_account_id,
        }
    }
    return {"auth_json": ("auth.json", json.dumps(auth_json), "application/json")}


async def _import(async_client, *, email: str, raw_account_id: str) -> str:
    response = await async_client.post(
        "/api/accounts/import",
        files=_auth_file(email=email, raw_account_id=raw_account_id),
    )
    assert response.status_code == 200, response.text
    return generate_unique_account_id(raw_account_id, email)


async def _listed_account(async_client, account_id: str) -> dict[str, Any]:
    response = await async_client.get("/api/accounts")
    assert response.status_code == 200
    return next(item for item in response.json()["accounts"] if item["accountId"] == account_id)


@pytest.mark.asyncio
async def test_account_weekly_empty_preference_defaults_updates_atomically_and_survives_reimport(
    async_client,
    monkeypatch,
):
    email = "weekly-empty-preference@example.com"
    raw_account_id = "acc_weekly_empty_preference"
    account_id = await _import(async_client, email=email, raw_account_id=raw_account_id)
    assert (await _listed_account(async_client, account_id))["autoRedeemResetCreditsWhenWeeklyExhausted"] is False

    audit: dict[str, object] = {}

    def capture_audit(action: str, **kwargs: object) -> None:
        audit.update(action=action, **kwargs)

    monkeypatch.setattr("app.modules.accounts.api.AuditService.log_async", capture_audit)
    update = await async_client.patch(
        f"/api/accounts/{account_id}",
        json={
            "securityWorkAuthorized": True,
            "autoRedeemResetCreditsWhenWeeklyExhausted": True,
        },
    )
    assert update.status_code == 200, update.text
    listed = await _listed_account(async_client, account_id)
    assert listed["securityWorkAuthorized"] is True
    assert listed["autoRedeemResetCreditsWhenWeeklyExhausted"] is True
    assert audit["action"] == "account_updated"
    details = audit["details"]
    assert isinstance(details, dict)
    assert set(details["changed_fields"]) == {
        "security_work_authorized",
        "auto_redeem_reset_credits_when_weekly_exhausted",
    }

    reimport = await async_client.post(
        "/api/accounts/import",
        files=_auth_file(email=email, raw_account_id=raw_account_id),
    )
    assert reimport.status_code == 200, reimport.text
    listed = await _listed_account(async_client, account_id)
    assert listed["securityWorkAuthorized"] is True
    assert listed["autoRedeemResetCreditsWhenWeeklyExhausted"] is True


@pytest.mark.asyncio
async def test_account_weekly_empty_preference_requires_polling_only_when_newly_enabled(
    async_client,
    monkeypatch,
):
    account_id = await _import(
        async_client,
        email="weekly-empty-polling@example.com",
        raw_account_id="acc_weekly_empty_polling",
    )
    monkeypatch.setattr(
        "app.modules.accounts.api.get_settings",
        lambda: SimpleNamespace(rate_limit_reset_credits_refresh_enabled=False),
    )

    unrelated = await async_client.patch(
        f"/api/accounts/{account_id}",
        json={"securityWorkAuthorized": True},
    )
    assert unrelated.status_code == 200
    disable = await async_client.patch(
        f"/api/accounts/{account_id}",
        json={"autoRedeemResetCreditsWhenWeeklyExhausted": False},
    )
    assert disable.status_code == 200
    rejected = await async_client.patch(
        f"/api/accounts/{account_id}",
        json={"autoRedeemResetCreditsWhenWeeklyExhausted": True},
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "reset_credit_polling_disabled"
    listed = await _listed_account(async_client, account_id)
    assert listed["securityWorkAuthorized"] is True
    assert listed["autoRedeemResetCreditsWhenWeeklyExhausted"] is False

    monkeypatch.setattr(
        "app.modules.accounts.api.get_settings",
        lambda: SimpleNamespace(rate_limit_reset_credits_refresh_enabled=True),
    )
    enabled = await async_client.patch(
        f"/api/accounts/{account_id}",
        json={"autoRedeemResetCreditsWhenWeeklyExhausted": True},
    )
    assert enabled.status_code == 200
    monkeypatch.setattr(
        "app.modules.accounts.api.get_settings",
        lambda: SimpleNamespace(rate_limit_reset_credits_refresh_enabled=False),
    )
    unchanged = await async_client.patch(
        f"/api/accounts/{account_id}",
        json={
            "securityWorkAuthorized": False,
            "autoRedeemResetCreditsWhenWeeklyExhausted": True,
        },
    )
    assert unchanged.status_code == 200
    listed = await _listed_account(async_client, account_id)
    assert listed["securityWorkAuthorized"] is False
    assert listed["autoRedeemResetCreditsWhenWeeklyExhausted"] is True


@pytest.mark.asyncio
async def test_account_weekly_empty_enable_rechecks_at_write_boundary_without_partial_update(
    async_client,
    monkeypatch,
):
    account_id = await _import(
        async_client,
        email="weekly-empty-race@example.com",
        raw_account_id="acc_weekly_empty_race",
    )
    enabled = await async_client.patch(
        f"/api/accounts/{account_id}",
        json={"autoRedeemResetCreditsWhenWeeklyExhausted": True},
    )
    assert enabled.status_code == 200
    monkeypatch.setattr(
        "app.modules.accounts.api.get_settings",
        lambda: SimpleNamespace(rate_limit_reset_credits_refresh_enabled=False),
    )
    original_update_account = AccountsService.update_account

    async def disable_immediately_before_guarded_write(
        self: AccountsService,
        requested_account_id: str,
        **kwargs: Any,
    ) -> bool:
        async with SessionLocal() as competing_session:
            await competing_session.execute(
                update(Account)
                .where(Account.id == requested_account_id)
                .values(auto_redeem_reset_credits_when_weekly_exhausted=False)
            )
            await competing_session.commit()
        return await original_update_account(self, requested_account_id, **kwargs)

    monkeypatch.setattr(
        AccountsService,
        "update_account",
        disable_immediately_before_guarded_write,
    )

    rejected = await async_client.patch(
        f"/api/accounts/{account_id}",
        json={
            "securityWorkAuthorized": True,
            "autoRedeemResetCreditsWhenWeeklyExhausted": True,
        },
    )

    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "reset_credit_polling_disabled"
    listed = await _listed_account(async_client, account_id)
    assert listed["autoRedeemResetCreditsWhenWeeklyExhausted"] is False
    assert listed["securityWorkAuthorized"] is False


@pytest.mark.asyncio
async def test_account_weekly_empty_preference_treats_pending_deletion_as_missing(
    async_client,
    monkeypatch,
):
    account_id = await _import(
        async_client,
        email="weekly-empty-deleted@example.com",
        raw_account_id="acc_weekly_empty_deleted",
    )
    async with SessionLocal() as session:
        account = await session.get(Account, account_id)
        assert account is not None
        account.delete_requested_at = utcnow()
        await session.commit()
    monkeypatch.setattr(
        "app.modules.accounts.api.get_settings",
        lambda: SimpleNamespace(rate_limit_reset_credits_refresh_enabled=False),
    )

    response = await async_client.patch(
        f"/api/accounts/{account_id}",
        json={"autoRedeemResetCreditsWhenWeeklyExhausted": True},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "account_not_found"
