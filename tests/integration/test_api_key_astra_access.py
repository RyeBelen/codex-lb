from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

import app.modules.proxy.api as proxy_api
import app.modules.proxy.service as proxy_module
from app.core.openai.model_registry import get_model_registry
from tests.integration.test_api_keys_api import _import_account, _make_upstream_model

pytestmark = pytest.mark.integration
ASTRA = "gpt-6-astra"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    [
        "/backend-api/codex/responses",
        "/v1/responses",
        "/v1/responses/",
        "/backend-api/codex/responses/compact",
        "/v1/responses/compact",
        "/v1/chat/completions",
    ],
)
@pytest.mark.parametrize("enforced", [False, True])
async def test_denied_before_quota_reservation(async_client, monkeypatch, path, enforced):
    await async_client.put("/api/settings", json={"apiKeyAuthEnabled": True})
    created = await async_client.post(
        "/api/api-keys/",
        json={
            "name": "disabled",
            "enforcedModel": ASTRA if enforced else None,
        },
    )
    assert created.status_code == 200
    assert created.json()["allowGpt6Astra"] is False

    async def unexpected_reservation(*args, **kwargs):
        pytest.fail("Denied Astra request attempted to reserve quota")

    monkeypatch.setattr(proxy_api, "_enforce_request_limits", unexpected_reservation)
    payload = {"model": "gpt-5.5" if enforced else ASTRA, "input": [], "instructions": "hi"}
    if "chat/completions" in path:
        payload = {"model": payload["model"], "messages": [{"role": "user", "content": "hi"}]}
    response = await async_client.post(path, headers={"Authorization": f"Bearer {created.json()['key']}"}, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "model_not_allowed"


@pytest.mark.asyncio
async def test_permission_lifecycle_and_catalogs(async_client, monkeypatch):
    models = [_make_upstream_model(slug) for slug in [ASTRA, "model-alpha"]]
    await get_model_registry().update({"pro": models, "plus": models})
    admin_catalog = await async_client.get("/api/models")
    assert ASTRA in [model["id"] for model in admin_catalog.json()["models"]]
    await async_client.put("/api/settings", json={"apiKeyAuthEnabled": True})
    key = (await async_client.post("/api/api-keys/", json={"name": "personal"})).json()
    headers = {"Authorization": f"Bearer {key['key']}"}
    other = (await async_client.post("/api/api-keys/", json={"name": "shared"})).json()

    async def assert_catalog(allowed, request_headers=headers):
        for path in ["/v1/models", "/v1/models?client_version=1.0.0", "/backend-api/codex/models"]:
            response = await async_client.get(path, headers=request_headers)
            assert response.status_code == 200
            body = response.json()
            assert (ASTRA in [m["id"] for m in body["data"]]) is allowed
            if "models" in body:
                assert (ASTRA in [m["slug"] for m in body["models"]]) is allowed

    await assert_catalog(False)
    enabled = await async_client.patch(f"/api/api-keys/{key['id']}", json={"allowGpt6Astra": True})
    assert enabled.json()["allowGpt6Astra"] is True
    await assert_catalog(True)
    await assert_catalog(False, {"Authorization": f"Bearer {other['key']}"})
    renamed = await async_client.patch(f"/api/api-keys/{key['id']}", json={"name": "renamed"})
    assert renamed.json()["allowGpt6Astra"] is True

    await _import_account(async_client, "acc_astra", "astra@example.com")
    seen = []

    async def fake_stream(payload, _headers, _access_token, _account_id, base_url=None, raise_for_status=False):
        seen.append(payload.model)
        event = {
            "type": "response.completed",
            "response": {
                "id": "resp_astra",
                "usage": {"input_tokens": 3, "output_tokens": 2},
            },
        }
        yield f"data: {json.dumps(event)}\n\n"

    monkeypatch.setattr(proxy_module, "core_stream_responses", fake_stream)
    response = await async_client.post(
        "/backend-api/codex/responses",
        headers=headers,
        json={"model": ASTRA, "instructions": "hi", "input": [], "stream": True},
    )
    assert response.status_code == 200
    assert seen == [ASTRA]
    await async_client.patch(f"/api/api-keys/{key['id']}", json={"allowedModels": ["model-alpha"]})
    blocked_by_allowlist = await async_client.post(
        "/v1/responses", headers=headers, json={"model": ASTRA, "input": "hi"}
    )
    assert blocked_by_allowlist.status_code == 403
    disabled = await async_client.patch(
        f"/api/api-keys/{key['id']}",
        json={
            "allowGpt6Astra": False,
            "allowedModels": [ASTRA, "model-alpha"],
            "applyToCodexModel": True,
        },
    )
    assert disabled.json()["allowGpt6Astra"] is False
    await assert_catalog(False)
    response = await async_client.post("/v1/responses", headers=headers, json={"model": ASTRA, "input": "hi"})
    assert response.status_code == 403
    assert seen == [ASTRA]


@pytest.mark.asyncio
async def test_no_authenticated_key_is_denied(async_client):
    response = await async_client.post("/v1/responses", json={"model": ASTRA, "input": "hi"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "model_not_allowed"


def test_websocket_denies_astra(app_instance):
    with TestClient(app_instance, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        client.put("/api/settings", json={"apiKeyAuthEnabled": True})
        key = client.post("/api/api-keys/", json={"name": "websocket"}).json()
        assert "key" in key, key
        with client.websocket_connect(
            "/backend-api/codex/responses",
            headers={
                "Authorization": f"Bearer {key['key']}",
            },
        ) as ws:
            ws.send_json({"type": "response.create", "model": ASTRA, "input": "hi"})
            result = ws.receive_json()
            assert result["error"]["code"] == "model_not_allowed"


@pytest.mark.asyncio
async def test_create_regenerate_and_null_update_preserve_permission(async_client):
    response = await async_client.post("/api/api-keys/", json={"name": "enabled", "allowGpt6Astra": True})
    assert response.status_code == 200
    key = response.json()
    assert key["allowGpt6Astra"] is True
    response = await async_client.patch(f"/api/api-keys/{key['id']}", json={"allowGpt6Astra": None})
    assert response.json()["allowGpt6Astra"] is True
    response = await async_client.post(f"/api/api-keys/{key['id']}/regenerate")
    assert response.status_code == 200
    assert response.json()["allowGpt6Astra"] is True
    assert response.json()["key"] != key["key"]
