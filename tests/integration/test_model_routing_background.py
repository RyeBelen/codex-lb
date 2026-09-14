import pytest

from app.core.clients.proxy import ProxyResponseError
from app.db.models import Account, AccountStatus
from app.db.session import SessionLocal
from app.modules.accounts.repository import AccountsRepository
from app.modules.limit_warmup.service import StreamingLimitWarmupSender
from app.modules.quota_planner.warmup import QuotaWarmupService
from tests.integration.test_account_api_key_access import _setup
from tests.integration.test_model_account_routing import _rule

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_background_warmup_senders_recheck_model_policy(async_client, monkeypatch):
    account_id, _, _ = await _setup(async_client)
    await _rule(async_client, [])
    calls = []

    async def unexpected(*args, **kwargs):
        calls.append(True)
        yield ""

    monkeypatch.setattr("app.modules.limit_warmup.service.stream_responses", unexpected)
    monkeypatch.setattr("app.modules.quota_planner.warmup.stream_responses", unexpected)
    async with SessionLocal() as session:
        account = await session.get(Account, account_id)
        account.limit_warmup_enabled = True
        await session.commit()
        sender = StreamingLimitWarmupSender(AccountsRepository(session))

        async def fresh(target):
            return target

        monkeypatch.setattr(sender, "_ensure_fresh", fresh)
        with pytest.raises(ProxyResponseError) as denied:
            await sender.send(account, model="gpt-5.1", prompt="ping")
        assert denied.value.status_code == 403
        with pytest.raises(ProxyResponseError) as denied:
            await QuotaWarmupService(session)._send_warmup_probe(account=account, model="gpt-5.1", request_id="probe")
        assert denied.value.status_code == 403
        assert account.status == AccountStatus.ACTIVE
    assert calls == []


@pytest.mark.asyncio
async def test_automation_ping_fails_without_inference_when_model_denied(async_client, monkeypatch):
    account_id, _, _ = await _setup(async_client)
    await _rule(async_client, [], model="gpt-5.6-sol")
    calls = []

    async def unexpected(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Denied automation reached upstream")

    monkeypatch.setattr("app.modules.automations.service.core_compact_responses", unexpected)
    created = await async_client.post(
        "/api/automations",
        json={
            "name": "Model scoped ping",
            "enabled": False,
            "schedule": {"type": "daily", "time": "05:00", "timezone": "UTC", "days": ["mon"]},
            "model": "gpt-5.6-sol",
            "prompt": "ping",
            "accountIds": [account_id],
        },
    )
    assert created.status_code == 200, created.text
    response = await async_client.post(f"/api/automations/{created.json()['id']}/run-now")
    assert response.status_code == 202, response.text
    assert response.json()["status"] == "failed", response.text
    assert calls == []
    async with SessionLocal() as session:
        account = await session.get(Account, account_id)
        assert account.status == AccountStatus.ACTIVE
