from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.modules.proxy.service as proxy_module
from app.core.clients.proxy import ProxyResponseError
from app.core.errors import openai_error
from app.core.openai.models import CompactResponsePayload
from app.db.models import Account, AccountStatus, ApiKeyUsageReservation
from app.db.session import SessionLocal
from tests.integration.test_account_api_key_access import _policy, _setup
from tests.integration.test_auth_middleware import _enable_guest_access
from tests.integration.test_proxy_sticky_sessions import _import_account

pytestmark = pytest.mark.integration
PATH = "/api/model-account-routing"


async def _rule(client, accounts, model="gpt-5.1", restricted=True):
    response = await client.put(PATH, json={"model": model, "restricted": restricted, "accountIds": accounts})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_rule_lifecycle_validation_and_account_deletion(async_client):
    account, _, _ = await _setup(async_client)
    assert (await async_client.get(PATH)).json() == {"rules": []}
    expected = {"model": "gpt-5.1", "restricted": True, "accountIds": [account]}
    assert await _rule(async_client, [account, account], " GPT-5.1 ") == expected
    for patch in [
        {"accountIds": ["missing"]},
        {"accountIds": [""]},
        {"accountIds": [None]},
        {"restricted": "false"},
        {"restricted": False},
        {"model": "*"},
        {"model": ""},
    ]:
        response = await async_client.put(PATH, json={**expected, **patch})
        assert response.status_code in (400, 422), response.text
        assert (await async_client.get(PATH)).json() == {"rules": [expected]}
    assert (await async_client.delete(f"/api/accounts/{account}")).status_code == 200
    expected["accountIds"] = []
    assert (await async_client.get(PATH)).json() == {"rules": [expected]}
    await _rule(async_client, [], restricted=False)
    assert (await async_client.get(PATH)).json() == {"rules": []}


@pytest.mark.asyncio
async def test_dashboard_auth_and_guest_read_only(async_client, app_instance):
    await _setup(async_client)
    assert (
        await async_client.post("/api/dashboard-auth/password/setup", json={"password": "password123"})
    ).status_code == 200
    transport = ASGITransport(app=app_instance, client=("203.0.113.20", 50001))
    async with AsyncClient(transport=transport, base_url="http://lb.example") as guest:
        assert (await guest.get(PATH)).status_code == 401
        body = {"model": "gpt-5.1", "restricted": True, "accountIds": []}
        assert (await guest.put(PATH, json=body)).status_code == 401
        await _enable_guest_access(async_client)
        assert (await guest.get(PATH)).status_code == 200
        assert (await guest.put(PATH, json=body)).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/v1/responses",
        "/backend-api/codex/responses",
        "/v1/chat/completions",
        "/v1/responses/compact",
        "/backend-api/codex/responses/compact",
    ],
)
async def test_inference_routes_restrict_only_configured_model(async_client, monkeypatch, path):
    account, _, headers = await _setup(async_client)
    await _import_account(async_client, "other", "other@example.com")
    await _rule(async_client, [account])
    seen = []

    async def stream(payload, _headers, _access_token, account_id, **kwargs):
        seen.append(account_id)
        yield (
            'data: {"type":"response.completed","response":{"id":"resp_rule","status":"completed",'
            '"output":[],"usage":{"input_tokens":1,"output_tokens":1}}}\n\n'
        )

    async def compact(payload, _headers, _access_token, account_id, **kwargs):
        seen.append(account_id)
        return CompactResponsePayload(id="resp_rule", object="response.compaction", output=[])

    monkeypatch.setattr(proxy_module, "core_stream_responses", stream)
    monkeypatch.setattr(proxy_module, "core_compact_responses", compact)
    payload = {"model": "gpt-5.1", "input": "hi", "instructions": "hi", "stream": True}
    if "chat/completions" in path:
        payload = {"model": "gpt-5.1", "messages": [{"role": "user", "content": "hi"}], "stream": True}
    elif "compact" in path:
        payload = {"model": "gpt-5.1", "input": [], "instructions": "hi"}
    response = await async_client.post(path, json=payload, headers=headers)
    assert response.status_code == 200, response.text
    assert seen == ["private"]
    await _rule(async_client, [])
    response = await async_client.post(path, json=payload, headers=headers)
    assert response.status_code >= 400 or '"error"' in response.text or "response.failed" in response.text
    assert seen == ["private"]
    response = await async_client.post(path, json={**payload, "model": "gpt-5.1-codex-mini"}, headers=headers)
    assert response.status_code == 200, response.text
    assert len(seen) == 2 and seen[-1] in ("private", "other")
    async with SessionLocal() as session:
        assert not list(
            await session.scalars(select(ApiKeyUsageReservation).where(ApiKeyUsageReservation.status == "reserved"))
        )


@pytest.mark.asyncio
async def test_intersects_key_and_account_permissions_and_forced_routing(async_client):
    account, key, headers = await _setup(async_client)
    other = await _import_account(async_client, "other", "other@example.com")
    await _rule(async_client, [account])
    await async_client.patch(f"/api/api-keys/{key['id']}", json={"assignedAccountIds": [other]})
    await async_client.put("/api/settings", json={"routingStrategy": "single_account", "singleAccountId": other})
    response = await async_client.post("/v1/responses", headers=headers, json={"model": "gpt-5.1", "input": "hi"})
    assert response.status_code >= 400
    await async_client.patch(f"/api/api-keys/{key['id']}", json={"assignedAccountIds": [account]})
    await _policy(async_client, account, [])
    response = await async_client.post("/v1/responses", headers=headers, json={"model": "gpt-5.1", "input": "hi"})
    assert response.status_code >= 400


@pytest.mark.asyncio
async def test_retry_cannot_leave_model_scope(async_client, monkeypatch):
    account, _, headers = await _setup(async_client)
    await _import_account(async_client, "other", "other@example.com")
    await _rule(async_client, [account])
    seen = []

    async def fail(payload, _headers, _access_token, account_id, **kwargs):
        seen.append(account_id)
        raise ProxyResponseError(503, openai_error("upstream_unavailable", "Unavailable"))
        yield ""

    monkeypatch.setattr(proxy_module, "core_stream_responses", fail)
    response = await async_client.post("/v1/responses", headers=headers, json={"model": "gpt-5.1", "input": "hi"})
    assert response.status_code >= 400
    assert seen and set(seen) == {"private"}


@pytest.mark.asyncio
async def test_enforced_model_and_no_api_key_cannot_bypass_rule(async_client, monkeypatch):
    _, key, headers = await _setup(async_client)
    await _rule(async_client, [])
    assert (
        await async_client.patch(f"/api/api-keys/{key['id']}", json={"enforcedModel": "gpt-5.1"})
    ).status_code == 200

    async def unexpected(*args, **kwargs):
        pytest.fail("Restricted model reached upstream")
        yield ""

    monkeypatch.setattr(proxy_module, "core_stream_responses", unexpected)
    response = await async_client.post("/v1/responses", headers=headers, json={"model": "gpt-5.2", "input": "hi"})
    assert response.status_code >= 400
    await async_client.put("/api/settings", json={"apiKeyAuthEnabled": False})
    response = await async_client.post("/v1/responses", json={"model": "gpt-5.1", "input": "hi"})
    assert response.status_code >= 400


@pytest.mark.asyncio
async def test_pending_deletion_remains_denied(async_client):
    from app.core.utils.time import utcnow
    from app.modules.model_routing.repository import ModelRoutingRepository

    account, _, _ = await _setup(async_client)
    await _rule(async_client, [account])
    async with SessionLocal() as session:
        row = await session.get(Account, account)
        row.delete_requested_at = utcnow()
        await session.commit()
        assert await ModelRoutingRepository(session).scope("gpt-5.1") == set()
    assert (
        await async_client.put(PATH, json={"model": "gpt-5.1", "restricted": True, "accountIds": [account]})
    ).status_code == 400


@pytest.mark.asyncio
async def test_revocation_during_retry_preserves_health_and_settles_usage(async_client, monkeypatch):
    account, _, headers = await _setup(async_client)
    await _rule(async_client, [account])
    seen = []

    async def stream(payload, _headers, _access_token, account_id, **kwargs):
        seen.append(account_id)
        await _rule(async_client, [])
        raise ProxyResponseError(503, openai_error("upstream_unavailable", "temporary failure"))
        yield ""

    monkeypatch.setattr(proxy_module, "core_stream_responses", stream)
    response = await async_client.post("/v1/responses", headers=headers, json={"model": "gpt-5.1", "input": "hi"})
    assert response.status_code >= 400
    assert seen == ["private"]
    async with SessionLocal() as session:
        assert not list(
            await session.scalars(select(ApiKeyUsageReservation).where(ApiKeyUsageReservation.status == "reserved"))
        )
        stored = await session.get(Account, account)
        assert stored.status == AccountStatus.ACTIVE
        assert stored.deactivation_reason is None


@pytest.mark.asyncio
@pytest.mark.parametrize("model", ["gpt-5.1", "gpt-5.1-high"])
async def test_warmup_filters_effective_model_including_alias(async_client, monkeypatch, model):
    from tests.integration.test_proxy_warmup import _add_primary_usage

    account, _, headers = await _setup(async_client)
    other = await _import_account(async_client, "other", "other@example.com")
    for account_id in (account, other):
        await _add_primary_usage(account_id, used_percent=0, window_minutes=300)
    assert (await async_client.put("/api/settings", json={"warmupModel": model})).status_code == 200
    await _rule(async_client, [account])
    seen = []

    async def compact(payload, _headers, _token, account_id, **kwargs):
        seen.append(account_id)
        return CompactResponsePayload(object="response.compaction", output=[])

    monkeypatch.setattr(proxy_module, "core_compact_responses", compact)
    response = await async_client.post("/v1/warmup/force", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["total_accounts"] == 1
    assert seen == ["private"]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/backend-api/transcribe", "/v1/audio/transcriptions"])
async def test_transcription_selects_only_allowed_accounts(async_client, monkeypatch, path):
    account, _, headers = await _setup(async_client)
    await _import_account(async_client, "other", "other@example.com")
    await _rule(async_client, [account], model="gpt-4o-transcribe")
    seen = []

    async def transcribe(*args, account_id, **kwargs):
        seen.append(account_id)
        return {"text": "hello"}

    monkeypatch.setattr(proxy_module, "core_transcribe_audio", transcribe)
    for allowed in (True, False):
        if not allowed:
            await _rule(async_client, [], model="gpt-4o-transcribe")
        response = await async_client.post(
            path,
            headers=headers,
            data={"model": "gpt-4o-transcribe"},
            files={"file": ("test.wav", b"audio", "audio/wav")},
        )
        assert response.status_code == 200 if allowed else response.status_code >= 400, response.text
        assert seen == ["private"]
