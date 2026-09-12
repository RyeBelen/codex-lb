from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.modules.proxy.service as proxy_module
from app.core.clients.proxy import ProxyResponseError
from app.core.clients.rate_limit_reset_credits import ResetCreditItem
from app.core.errors import openai_error
from app.core.openai.models import CompactResponsePayload
from app.db.models import Account, AccountApiKeyGrant, AccountStatus, ApiKeyUsageReservation, UsageHistory
from app.db.session import SessionLocal
from tests.integration.test_auth_middleware import _enable_guest_access
from tests.integration.test_proxy_sticky_sessions import _import_account
from tests.integration.test_proxy_warmup import _add_primary_usage
from tests.integration.test_v1_reset_credit import _seed_snapshot

pytestmark = pytest.mark.integration


async def _setup(client):
    account = await _import_account(client, "private", "private@example.com")
    key = (await client.post("/api/api-keys/", json={"name": "personal"})).json()
    await client.put("/api/settings", json={"apiKeyAuthEnabled": True})
    return account, key, {"Authorization": f"Bearer {key['key']}"}


async def _policy(client, account, keys, restricted=True):
    response = await client.put(
        f"/api/accounts/{account}/api-key-access", json={"restricted": restricted, "apiKeyIds": keys}
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_policy_lifecycle_preserves_independent_key_scope(async_client):
    account, key, _ = await _setup(async_client)
    path = f"/api/accounts/{account}/api-key-access"
    assert (await async_client.get(path)).json() == {"accountId": account, "restricted": False, "apiKeyIds": []}
    assert (await _policy(async_client, account, [key["id"], key["id"]]))["apiKeyIds"] == [key["id"]]
    listed = (await async_client.get("/api/api-keys/")).json()
    assert listed[0]["accountAssignmentScopeEnabled"] is False
    assert listed[0]["assignedAccountIds"] == []
    before = (await async_client.get(path)).json()
    for body in [
        {"restricted": True, "apiKeyIds": ["missing"]},
        {"restricted": False, "apiKeyIds": [key["id"]]},
        {"restricted": "false", "apiKeyIds": []},
        {"restricted": True, "apiKeyIds": [""]},
        {"restricted": True, "apiKeyIds": [None]},
    ]:
        result = await async_client.put(path, json=body)
        assert result.status_code in (400, 422)
        assert (await async_client.get(path)).json() == before
    regenerated = await async_client.post(f"/api/api-keys/{key['id']}/regenerate")
    assert regenerated.status_code == 200
    assert (await async_client.get(path)).json() == before
    await async_client.delete(f"/api/api-keys/{key['id']}")
    assert (await async_client.get(path)).json() == {"accountId": account, "restricted": True, "apiKeyIds": []}
    await _policy(async_client, account, [], restricted=False)
    assert (await async_client.get(path)).json()["restricted"] is False
    assert (await async_client.get("/api/accounts/missing/api-key-access")).status_code == 404
    assert (
        await async_client.put("/api/accounts/missing/api-key-access", json={"restricted": True, "apiKeyIds": []})
    ).status_code == 404


@pytest.mark.asyncio
async def test_account_deletion_cascades_grants(async_client):
    account, key, _ = await _setup(async_client)
    await _policy(async_client, account, [key["id"]])
    response = await async_client.delete(f"/api/accounts/{account}")
    assert response.status_code == 200, response.text
    path = f"/api/accounts/{account}/api-key-access"
    assert (await async_client.get(path)).status_code == 404
    assert (await async_client.put(path, json={"restricted": False, "apiKeyIds": []})).status_code == 404
    async with SessionLocal() as session:
        assert not list(await session.scalars(select(AccountApiKeyGrant)))


@pytest.mark.asyncio
async def test_access_endpoints_require_dashboard_auth(async_client, app_instance):
    account, _, _ = await _setup(async_client)
    result = await async_client.post("/api/dashboard-auth/password/setup", json={"password": "password123"})
    assert result.status_code == 200
    transport = ASGITransport(app=app_instance, client=("203.0.113.20", 50001))
    async with AsyncClient(transport=transport, base_url="http://lb.example") as anonymous:
        path = f"/api/accounts/{account}/api-key-access"
        assert (await anonymous.get(path)).status_code == 401
        assert (await anonymous.put(path, json={"restricted": True, "apiKeyIds": []})).status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/backend-api/codex/responses",
        "/v1/responses",
        "/v1/chat/completions",
        "/backend-api/codex/responses/compact",
        "/v1/responses/compact",
        "/backend-api/files",
    ],
)
async def test_routes_enforce_grants_and_revocation(async_client, monkeypatch, path):
    account, key, headers = await _setup(async_client)
    await _policy(async_client, account, [key["id"]])
    seen = []

    async def stream(payload, _headers, _access_token, account_id, **kwargs):
        seen.append(account_id)
        yield (
            'data: {"type":"response.completed","response":{"id":"resp_access","status":"completed",'
            '"output":[],"usage":{"input_tokens":1,"output_tokens":1}}}\n\n'
        )

    async def compact(payload, _headers, _access_token, account_id, **kwargs):
        seen.append(account_id)
        return CompactResponsePayload(id="resp_compact", object="response.compaction", output=[])

    async def file(*, account_id, **kwargs):
        seen.append(account_id)
        return {"file_id": "file-access", "upload_url": "https://example.invalid/upload"}

    monkeypatch.setattr(proxy_module, "core_stream_responses", stream)
    monkeypatch.setattr(proxy_module, "core_compact_responses", compact)
    monkeypatch.setattr(proxy_module, "core_create_file", file)
    payload = {"model": "gpt-5.1", "input": "hi", "instructions": "hi", "stream": True}
    if "chat/completions" in path:
        payload = {"model": "gpt-5.1", "messages": [{"role": "user", "content": "hi"}], "stream": True}
    elif "compact" in path:
        payload = {"model": "gpt-5.1", "input": [], "instructions": "hi"}
    elif path.endswith("files"):
        payload = {"file_name": "test.txt", "file_size": 10, "use_case": "codex"}
    response = await async_client.post(path, json=payload, headers=headers)
    assert response.status_code == 200, response.text
    assert seen == ["private"], response.text
    await _policy(async_client, account, [])
    response = await async_client.post(path, json=payload, headers=headers)
    assert seen == ["private"], response.text
    assert response.status_code >= 400 or "response.failed" in response.text or '"error"' in response.text
    async with SessionLocal() as session:
        reservations = list(
            await session.scalars(select(ApiKeyUsageReservation).where(ApiKeyUsageReservation.status == "reserved"))
        )
        assert reservations == []


@pytest.mark.asyncio
async def test_new_keys_and_no_key_cannot_use_reserved_account(async_client, monkeypatch):
    account, key, _ = await _setup(async_client)
    await _policy(async_client, account, [key["id"]])
    new_key = (await async_client.post("/api/api-keys/", json={"name": "new"})).json()

    async def unexpected(*args, **kwargs):
        pytest.fail("Forbidden inference reached upstream")
        yield ""

    monkeypatch.setattr(proxy_module, "core_stream_responses", unexpected)
    payload = {"model": "gpt-5.1", "input": "hi"}
    for headers in [{"Authorization": f"Bearer {new_key['key']}"}, {}]:
        if not headers:
            await async_client.put("/api/settings", json={"apiKeyAuthEnabled": False})
        result = await async_client.post("/v1/responses", headers=headers, json=payload)
        assert result.status_code >= 400 or '"error"' in result.text


@pytest.mark.asyncio
async def test_scope_intersection_and_single_account_do_not_bypass_grants(async_client, monkeypatch):
    account, key, headers = await _setup(async_client)
    other = await _import_account(async_client, "shared", "shared@example.com")
    await _policy(async_client, account, [key["id"]])
    await async_client.patch(f"/api/api-keys/{key['id']}", json={"assignedAccountIds": [other]})
    await async_client.put("/api/settings", json={"routingStrategy": "single_account", "singleAccountId": account})
    result = await async_client.post("/v1/responses", headers=headers, json={"model": "gpt-5.1", "input": "hi"})
    assert result.status_code >= 400

    await async_client.patch(f"/api/api-keys/{key['id']}", json={"assignedAccountIds": [account]})
    await _policy(async_client, account, [])
    result = await async_client.post("/v1/responses", headers=headers, json={"model": "gpt-5.1", "input": "hi"})
    assert result.status_code >= 400


@pytest.mark.asyncio
async def test_failover_never_uses_restricted_account(async_client, monkeypatch):
    account, key, headers = await _setup(async_client)
    forbidden = await _import_account(async_client, "forbidden", "forbidden@example.com")
    await _policy(async_client, account, [key["id"]])
    await _policy(async_client, forbidden, [])
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
async def test_revoked_file_pin_does_not_move_to_shared_account(async_client, monkeypatch):
    account, key, headers = await _setup(async_client)
    await _policy(async_client, account, [key["id"]])
    finalized = []

    async def create(**kwargs):
        return {"file_id": "file-access-pin", "upload_url": "https://example.invalid/upload"}

    async def finalize(**kwargs):
        finalized.append(kwargs)
        return {"status": "success"}

    monkeypatch.setattr(proxy_module, "core_create_file", create)
    monkeypatch.setattr(proxy_module, "core_finalize_file", finalize)
    created = await async_client.post(
        "/backend-api/files", headers=headers, json={"file_name": "a.txt", "file_size": 10, "use_case": "codex"}
    )
    assert created.status_code == 200
    await _policy(async_client, account, [])
    await _import_account(async_client, "shared", "shared@example.com")
    result = await async_client.post("/backend-api/files/file-access-pin/uploaded", headers=headers, json={})
    assert result.status_code >= 400
    assert finalized == []


@pytest.mark.asyncio
async def test_account_pool_usage_excludes_forbidden_capacity(async_client):
    account, key, headers = await _setup(async_client)
    shared = await _import_account(async_client, "shared", "shared@example.com")
    await _policy(async_client, account, [])
    async with SessionLocal() as session:
        session.add_all(
            [
                UsageHistory(account_id=account, window="primary", used_percent=90.0, window_minutes=300),
                UsageHistory(account_id=shared, window="primary", used_percent=20.0, window_minutes=300),
                UsageHistory(account_id=account, window="secondary", used_percent=90.0, window_minutes=10080),
                UsageHistory(account_id=shared, window="secondary", used_percent=30.0, window_minutes=10080),
            ]
        )
        await session.commit()
    response = await async_client.get("/v1/usage", headers=headers)
    assert response.status_code == 200
    assert response.json()["account_pool_usage"] == {"primary": 80.0, "secondary": 70.0}


@pytest.mark.asyncio
async def test_guest_cannot_change_account_access(async_client, app_instance):
    account, key, _ = await _setup(async_client)
    await _enable_guest_access(async_client)
    transport = ASGITransport(app=app_instance, client=("203.0.113.20", 50001))
    async with AsyncClient(transport=transport, base_url="http://lb.example") as guest:
        path = f"/api/accounts/{account}/api-key-access"
        assert (await guest.get(path)).status_code == 200
        assert (await guest.put(path, json={"restricted": True, "apiKeyIds": [key["id"]]})).status_code == 403
    assert (await async_client.get(path)).json()["restricted"] is False


@pytest.mark.asyncio
async def test_warmup_and_reset_cannot_target_restricted_account(async_client, monkeypatch):
    account, key, headers = await _setup(async_client)
    await _policy(async_client, account, [])
    await _add_primary_usage(account, used_percent=0, window_minutes=300)
    calls = []

    async def compact(*args, **kwargs):
        calls.append(kwargs)
        return CompactResponsePayload.model_validate({"object": "response.compaction", "output": []})

    monkeypatch.setattr(proxy_module, "core_compact_responses", compact)
    warmup = await async_client.post("/v1/warmup/force", headers=headers)
    assert warmup.status_code == 200, warmup.text
    assert warmup.json()["total_accounts"] == 0
    assert calls == []
    reset = await async_client.post(
        "/v1/reset-credit", headers=headers, json={"account_id": account, "redeem_id": "credit-private"}
    )
    assert reset.status_code == 403, reset.text


@pytest.mark.asyncio
async def test_reset_credit_listing_excludes_restricted_accounts(async_client):
    account, key, headers = await _setup(async_client)
    shared = await _import_account(async_client, "shared", "shared@example.com")
    for account_id in (account, shared):
        await _seed_snapshot(
            account_id, available_count=1, credits=[ResetCreditItem(id=f"credit-{account_id}", status="available")]
        )
    await _policy(async_client, account, [])
    response = await async_client.get("/v1/reset-credit", headers=headers)
    assert response.status_code == 200
    assert [entry["account_id"] for entry in response.json()] == [shared]


@pytest.mark.asyncio
async def test_revocation_during_retry_stops_same_account_and_preserves_health(async_client, monkeypatch):
    account, key, headers = await _setup(async_client)
    await _policy(async_client, account, [key["id"]])
    seen = []

    async def stream(payload, _headers, _access_token, account_id, **kwargs):
        seen.append(account_id)
        await _policy(async_client, account, [])
        raise ProxyResponseError(503, openai_error("upstream_unavailable", "temporary upstream failure"))
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
        assert stored is not None
        assert stored.status == AccountStatus.ACTIVE
        assert stored.deactivation_reason is None
