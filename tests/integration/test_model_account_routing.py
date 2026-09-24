from __future__ import annotations

from dataclasses import replace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.modules.proxy.service as proxy_module
from app.core.clients.proxy import ProxyResponseError
from app.core.errors import openai_error
from app.core.openai.model_registry import ModelRegistrySnapshot, get_model_registry
from app.core.openai.models import CompactResponsePayload
from app.db.models import Account, AccountStatus, ApiKeyUsageReservation
from app.db.session import SessionLocal
from tests.integration.test_account_api_key_access import _policy, _setup
from tests.integration.test_auth_middleware import _enable_guest_access
from tests.integration.test_proxy_sticky_sessions import _import_account

pytestmark = pytest.mark.integration
PATH = "/api/model-account-routing"


def _set_account_catalog(monkeypatch, catalogs: dict[str, list[tuple[str, str]]]) -> None:
    registry = get_model_registry()
    template = next(iter(registry.get_models_for_metadata().values()))
    models = {
        slug: replace(template, slug=slug, display_name=name) for entries in catalogs.values() for slug, name in entries
    }
    model_accounts = {
        slug: frozenset(
            account_id for account_id, entries in catalogs.items() if any(item[0] == slug for item in entries)
        )
        for slug in models
    }
    snapshot = ModelRegistrySnapshot(
        models=models,
        model_plans={slug: frozenset({"pro"}) for slug in models},
        plan_models={"pro": frozenset(models)},
        model_service_tier_plans={},
        model_service_tier_accounts={},
        account_plans={account_id: "pro" for account_id in catalogs},
        fetched_at=0,
        model_accounts=model_accounts,
        account_catalogs_authoritative=True,
    )
    monkeypatch.setattr(registry, "_snapshot", snapshot)


async def _rule(client, accounts, model="gpt-5.1", restricted=True):
    response = await client.put(PATH, json={"model": model, "restricted": restricted, "accountIds": accounts})
    assert response.status_code == 200, response.text
    return response.json()


async def _reserve_elsewhere(client, account, model="gpt-5.1"):
    await _rule(client, [], model=model, restricted=False)
    await _rule(client, [account], model="gpt-6-astra")


@pytest.mark.asyncio
async def test_account_allowed_models_replace_is_atomic_and_preserves_other_accounts(async_client, monkeypatch):
    from app.core.utils.time import utcnow

    account, _, _ = await _setup(async_client)
    other = await _import_account(async_client, "other", "other@example.com")
    _set_account_catalog(
        monkeypatch,
        {
            account: [("gpt-6-astra", "GPT-6 Astra"), ("gpt-6-sol", "GPT-6 Sol")],
            other: [("gpt-6-astra", "GPT-6 Astra")],
        },
    )
    await _rule(async_client, [account, other], model="gpt-6-astra")

    path = f"/api/accounts/{account}/allowed-models"
    assert (await async_client.get(path)).json() == {
        "accountId": account,
        "allowedModels": ["gpt-6-astra"],
        "availableModels": [
            {"id": "gpt-6-astra", "name": "GPT-6 Astra"},
            {"id": "gpt-6-sol", "name": "GPT-6 Sol"},
        ],
        "catalogAvailable": True,
    }

    replaced = await async_client.put(path, json={"allowedModels": ["gpt-6-sol", "gpt-6-sol"]})
    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["allowedModels"] == ["gpt-6-sol"]
    assert (await async_client.get(PATH)).json()["rules"] == [
        {"model": "gpt-6-astra", "restricted": True, "accountIds": [other]},
        {"model": "gpt-6-sol", "restricted": True, "accountIds": [account]},
    ]

    cleared = await async_client.put(path, json={"allowedModels": []})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["allowedModels"] == []
    assert (await async_client.get(PATH)).json()["rules"] == [
        {"model": "gpt-6-astra", "restricted": True, "accountIds": [other]}
    ]
    async with SessionLocal() as session:
        stored = await session.get(Account, account)
        stored.delete_requested_at = utcnow()
        await session.commit()
    assert (await async_client.get(path)).status_code == 404
    assert (await async_client.put(path, json={"allowedModels": []})).status_code == 404


@pytest.mark.asyncio
async def test_account_allowed_models_preserves_visible_stale_selection_and_rejects_new_unknown(
    async_client, monkeypatch
):
    account, _, _ = await _setup(async_client)
    await _rule(async_client, [account], model="retired-model")
    _set_account_catalog(monkeypatch, {account: [("gpt-6-sol", "GPT-6 Sol")]})
    path = f"/api/accounts/{account}/allowed-models"

    policy = (await async_client.get(path)).json()
    assert policy["allowedModels"] == ["retired-model"]
    assert policy["availableModels"] == [{"id": "gpt-6-sol", "name": "GPT-6 Sol"}]
    assert (await async_client.put(path, json={"allowedModels": ["retired-model"]})).status_code == 200
    rejected = await async_client.put(path, json={"allowedModels": ["unknown-model"]})
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "invalid_account_models"
    assert (await async_client.get(path)).json()["allowedModels"] == ["retired-model"]
    assert (await async_client.put(path, json={"allowedModels": []})).status_code == 200


@pytest.mark.asyncio
async def test_account_allowed_models_distinguishes_unavailable_catalog_and_authorization(
    async_client, app_instance, monkeypatch
):
    account, _, _ = await _setup(async_client)
    _set_account_catalog(monkeypatch, {account: []})
    path = f"/api/accounts/{account}/allowed-models"
    empty = await async_client.get(path)
    assert empty.status_code == 200
    assert empty.json()["catalogAvailable"] is True
    assert empty.json()["availableModels"] == []
    assert (await async_client.put(path, json={"allowedModels": []})).status_code == 200

    _set_account_catalog(monkeypatch, {})
    policy = await async_client.get(path)
    assert policy.status_code == 200
    assert policy.json()["catalogAvailable"] is False
    unavailable = await async_client.put(path, json={"allowedModels": []})
    assert unavailable.status_code == 409
    assert unavailable.json()["error"]["code"] == "account_model_catalog_unavailable"
    assert (await async_client.get("/api/accounts/missing/allowed-models")).status_code == 404

    assert (
        await async_client.post("/api/dashboard-auth/password/setup", json={"password": "password123"})
    ).status_code == 200
    transport = ASGITransport(app=app_instance, client=("203.0.113.20", 50001))
    async with AsyncClient(transport=transport, base_url="http://lb.example") as guest:
        assert (await guest.get(path)).status_code == 401
        assert (await guest.put(path, json={"allowedModels": []})).status_code == 401
        await _enable_guest_access(async_client)
        assert (await guest.get(path)).status_code == 200
        assert (await guest.put(path, json={"allowedModels": []})).status_code == 403


@pytest.mark.asyncio
async def test_reservation_union_empty_rules_new_accounts_and_release(async_client):
    from app.modules.model_routing.repository import ModelRoutingRepository

    account, _, _ = await _setup(async_client)
    await _rule(async_client, [])
    async with SessionLocal() as session:
        assert await ModelRoutingRepository(session).scope("gpt-5.1") is None
    await _rule(async_client, [account])
    await _rule(async_client, [account], model="gpt-6-astra")
    other = await _import_account(async_client, "new", "new@example.com")
    async with SessionLocal() as session:
        repo = ModelRoutingRepository(session)
        assert await repo.scope(" GPT-6-ASTRA ") == {account, other}
        assert await repo.scope("gpt-5.1") == {account, other}
        assert await repo.scope("gpt-5.6-sol") == {other}
        assert await repo.scope(None, allow_model_less=False) == {other}
        assert await repo.scope(None) is None
    await _rule(async_client, [], restricted=False)
    async with SessionLocal() as session:
        repo = ModelRoutingRepository(session)
        assert await repo.scope("gpt-5.1") == {other}
        assert await repo.scope("gpt-6-astra") == {account, other}
    await _rule(async_client, [], model="gpt-6-astra", restricted=False)
    async with SessionLocal() as session:
        assert await ModelRoutingRepository(session).scope("gpt-5.6-sol") is None


@pytest.mark.asyncio
async def test_unknown_model_realtime_excludes_reserved_accounts(async_client, monkeypatch):
    from app.core.clients.proxy import CodexControlResponse

    account, key, headers = await _setup(async_client)
    await _rule(async_client, [account], model="gpt-6-astra")
    seen = []

    async def control(*args, account_id, **kwargs):
        seen.append(account_id)
        return CodexControlResponse(
            status_code=201,
            body=b"v=answer\r\n",
            headers={"content-type": "application/sdp", "location": "/v1/realtime/calls/rtc_reserved"},
        )

    monkeypatch.setattr(proxy_module, "core_codex_control_request", control)
    path = "/backend-api/codex/realtime/calls"
    request_headers = {**headers, "content-type": "application/sdp"}
    denied = await async_client.post(path, content=b"v=offer\r\n", headers=request_headers)
    assert denied.status_code >= 400, denied.text
    assert seen == []
    await _import_account(async_client, "unreserved", "unreserved@example.com")
    allowed = await async_client.post(path, content=b"v=offer\r\n", headers=request_headers)
    assert allowed.status_code == 201, allowed.text
    assert seen == ["unreserved"]


@pytest.mark.asyncio
async def test_model_less_files_keep_reserved_account_ownership(async_client, monkeypatch):
    account, _, headers = await _setup(async_client)
    await _rule(async_client, [account], model="gpt-6-astra")
    seen = []

    async def create(*, account_id, **kwargs):
        seen.append(account_id)
        return {"file_id": "file-reserved", "upload_url": "https://example.invalid/upload"}

    async def finalize(*, account_id, **kwargs):
        seen.append(account_id)
        return {"status": "success"}

    monkeypatch.setattr(proxy_module, "core_create_file", create)
    monkeypatch.setattr(proxy_module, "core_finalize_file", finalize)
    created = await async_client.post(
        "/backend-api/files", headers=headers, json={"file_name": "a.txt", "file_size": 10, "use_case": "codex"}
    )
    assert created.status_code == 200, created.text
    finalized = await async_client.post("/backend-api/files/file-reserved/uploaded", headers=headers, json={})
    assert finalized.status_code == 200, finalized.text
    assert seen == ["private", "private"]


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
async def test_accounts_are_reserved_but_model_can_use_other_accounts(async_client, monkeypatch, path):
    account, key, headers = await _setup(async_client)
    other = await _import_account(async_client, "other", "other@example.com")
    await _rule(async_client, [account])
    await async_client.patch(f"/api/api-keys/{key['id']}", json={"assignedAccountIds": [account]})
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
    other_payload = {**payload, "model": "gpt-5.1-codex-mini"}
    response = await async_client.post(path, json=other_payload, headers=headers)
    assert response.status_code >= 400 or '"error"' in response.text or "response.failed" in response.text
    assert seen == ["private"]
    await async_client.patch(f"/api/api-keys/{key['id']}", json={"assignedAccountIds": [other]})
    response = await async_client.post(path, json=payload, headers=headers)
    assert response.status_code == 200, response.text
    assert seen == ["private", "other"]
    await _rule(async_client, [], restricted=False)
    await async_client.patch(f"/api/api-keys/{key['id']}", json={"assignedAccountIds": [account]})
    response = await async_client.post(path, json=other_payload, headers=headers)
    assert response.status_code == 200, response.text
    assert seen == ["private", "other", "private"]
    async with SessionLocal() as session:
        assert not list(
            await session.scalars(select(ApiKeyUsageReservation).where(ApiKeyUsageReservation.status == "reserved"))
        )


@pytest.mark.asyncio
async def test_intersects_key_and_account_permissions_and_forced_routing(async_client):
    account, key, headers = await _setup(async_client)
    other = await _import_account(async_client, "other", "other@example.com")
    await _rule(async_client, [account])
    await _rule(async_client, [other], model="gpt-6-astra")
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
    other = await _import_account(async_client, "other", "other@example.com")
    await _rule(async_client, [account])
    await _rule(async_client, [other], model="gpt-6-astra")
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
    account, key, headers = await _setup(async_client)
    await _rule(async_client, [account], model="gpt-6-astra")
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
        await _reserve_elsewhere(async_client, account)
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
    await _rule(async_client, [other], model="gpt-6-astra")
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
    other = await _import_account(async_client, "other", "other@example.com")
    await _rule(async_client, [account], model="gpt-4o-transcribe")
    await _rule(async_client, [other], model="gpt-6-astra")
    seen = []

    async def transcribe(*args, account_id, **kwargs):
        seen.append(account_id)
        return {"text": "hello"}

    monkeypatch.setattr(proxy_module, "core_transcribe_audio", transcribe)
    for allowed in (True, False):
        if not allowed:
            await _rule(async_client, [], model="gpt-4o-transcribe", restricted=False)
            await _rule(async_client, [account, other], model="gpt-6-astra")
        response = await async_client.post(
            path,
            headers=headers,
            data={"model": "gpt-4o-transcribe"},
            files={"file": ("test.wav", b"audio", "audio/wav")},
        )
        assert response.status_code == 200 if allowed else response.status_code >= 400, response.text
        assert seen == ["private"]
