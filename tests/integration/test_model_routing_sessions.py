from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.modules.proxy.service as proxy_module
from app.db.models import ApiKeyUsageReservation
from app.db.session import SessionLocal
from app.dependencies import get_proxy_service_for_app
from tests.integration.test_account_api_key_access import _setup
from tests.integration.test_http_responses_bridge import _FakeBridgeUpstreamWebSocket, _install_bridge_settings
from tests.integration.test_model_account_routing import _rule
from tests.integration.test_proxy_sticky_sessions import _make_auth_json

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
async def test_http_bridge_revocation_blocks_reused_connection(async_client, app_instance, monkeypatch, path):
    account, key, headers = await _setup(async_client)
    await _rule(async_client, [account])
    _install_bridge_settings(monkeypatch, enabled=True)
    upstream = _FakeBridgeUpstreamWebSocket()
    connections = []

    async def connect(headers, access_token, account_id, **kwargs):
        connections.append(account_id)
        return upstream

    monkeypatch.setattr(proxy_module, "connect_responses_websocket", connect)
    payload = {"model": "gpt-5.1", "input": "hello", "instructions": "hi", "prompt_cache_key": "access-test"}
    if "backend-api" in path:
        payload["stream"] = True
    service = get_proxy_service_for_app(app_instance)
    try:
        first = await async_client.post(path, headers=headers, json=payload)
        assert first.status_code == 200, first.text
        assert "resp_bridge_1" in first.text
        assert len(upstream.sent_text) == 1
        await _rule(async_client, [])
        second = await async_client.post(
            path, headers=headers, json={**payload, "previous_response_id": "resp_bridge_1"}
        )
        assert len(upstream.sent_text) == 1, second.text
        assert second.status_code >= 400 or '"error"' in second.text
        assert connections == ["private"]

        async with SessionLocal() as session:
            assert not list(
                await session.scalars(select(ApiKeyUsageReservation).where(ApiKeyUsageReservation.status == "reserved"))
            )
    finally:
        for bridge in list(service._http_bridge_sessions.values()):
            await service._close_http_bridge_session(bridge)


@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
def test_websocket_revocation_blocks_next_turn(app_instance, monkeypatch, path):
    upstream = _FakeBridgeUpstreamWebSocket()
    connections = []

    async def connect(headers, access_token, account_id, **kwargs):
        connections.append(account_id)
        return upstream

    monkeypatch.setattr(proxy_module, "connect_responses_websocket", connect)
    with TestClient(app_instance, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        auth = _make_auth_json("private", "private@example.com")
        imported = client.post("/api/accounts/import", files={"auth_json": ("auth.json", json.dumps(auth))})
        account = imported.json()["accountId"]
        key = client.post("/api/api-keys/", json={"name": "socket"}).json()
        client.put("/api/settings", json={"apiKeyAuthEnabled": True})
        access_path = "/api/model-account-routing"
        assert (
            client.put(access_path, json={"model": "gpt-5.1", "restricted": True, "accountIds": [account]}).status_code
            == 200
        )
        with client.websocket_connect(path, headers={"Authorization": f"Bearer {key['key']}"}) as ws:
            payload = {"type": "response.create", "model": "gpt-5.1", "input": "hello", "instructions": "hi"}
            ws.send_json(payload)
            messages = [ws.receive_json() for _ in range(2)]
            assert messages[-1]["type"] == "response.completed", messages
            assert len(upstream.sent_text) == 1
            assert (
                client.put(access_path, json={"model": "gpt-5.1", "restricted": True, "accountIds": []}).status_code
                == 200
            )
            ws.send_json({**payload, "previous_response_id": "resp_bridge_1"})
            denied = ws.receive_json()
            assert denied["type"] in ("error", "response.failed"), denied
            assert len(upstream.sent_text) == 1
        assert connections == ["private"]
