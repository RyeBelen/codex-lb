from __future__ import annotations

import asyncio
import json
import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from starlette.testclient import WebSocketDenialResponse

import app.modules.proxy.service as proxy_module
from app.core.clients.proxy import CodexControlResponse
from app.core.clients.proxy_websocket import UpstreamWebSocketMessage
from app.db.models import ApiKeyUsageReservation
from app.db.session import SessionLocal
from app.dependencies import get_proxy_service_for_app
from tests.integration.test_account_api_key_access import _policy, _setup
from tests.integration.test_http_responses_bridge import _FakeBridgeUpstreamWebSocket, _install_bridge_settings
from tests.integration.test_proxy_sticky_sessions import _make_auth_json

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/v1/responses", "/backend-api/codex/responses"])
async def test_http_bridge_revocation_blocks_reused_connection(async_client, app_instance, monkeypatch, path):
    account, key, headers = await _setup(async_client)
    await _policy(async_client, account, [key["id"]])
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
        await _policy(async_client, account, [])
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
        access_path = f"/api/accounts/{account}/api-key-access"
        assert client.put(access_path, json={"restricted": True, "apiKeyIds": [key["id"]]}).status_code == 200
        with client.websocket_connect(path, headers={"Authorization": f"Bearer {key['key']}"}) as ws:
            payload = {"type": "response.create", "model": "gpt-5.1", "input": "hello", "instructions": "hi"}
            ws.send_json(payload)
            messages = [ws.receive_json() for _ in range(2)]
            assert messages[-1]["type"] == "response.completed", messages
            assert len(upstream.sent_text) == 1
            assert client.put(access_path, json={"restricted": True, "apiKeyIds": []}).status_code == 200
            ws.send_json({**payload, "previous_response_id": "resp_bridge_1"})
            denied = ws.receive_json()
            assert denied["type"] in ("error", "response.failed"), denied
            assert len(upstream.sent_text) == 1
        assert connections == ["private"]


@pytest.mark.parametrize(
    "path", ["/v1/live/rtc_access", "/v1/realtime?call_id=rtc_access", "/backend-api/codex/rtc_access"]
)
@pytest.mark.parametrize("binary", [False, True])
def test_realtime_revocation_blocks_frames_and_reattachment(app_instance, monkeypatch, path, binary):
    class Upstream:
        def __init__(self):
            self.frames = []
            self.messages = asyncio.Queue()
            self.closed = threading.Event()

        async def send_text(self, value):
            self.frames.append(value)
            self.messages.put_nowait(UpstreamWebSocketMessage(kind="text", text="accepted"))

        async def send_bytes(self, value):
            await self.send_text(value)

        async def receive(self):
            return await self.messages.get()

        async def close(self, code=1000, reason=""):
            self.closed.set()

        def response_header(self, name):
            return None

    upstream = Upstream()
    connections = []

    async def control(*args, **kwargs):
        return CodexControlResponse(
            status_code=201,
            body=b"v=answer\r\n",
            headers={"content-type": "application/sdp", "location": "/v1/realtime/calls/rtc_access"},
        )

    async def connect(*args, **kwargs):
        connections.append(True)
        return upstream

    monkeypatch.setattr(proxy_module, "core_codex_control_request", control)
    with TestClient(app_instance, base_url="http://localhost", client=("127.0.0.1", 50000)) as client:
        service = get_proxy_service_for_app(app_instance)
        monkeypatch.setattr(service, "_live_websocket_connector", connect)
        released = threading.Event()
        release = service._load_balancer.release_account_lease

        async def release_lease(lease):
            await release(lease)
            released.set()

        monkeypatch.setattr(service._load_balancer, "release_account_lease", release_lease)
        imported = client.post(
            "/api/accounts/import",
            files={"auth_json": ("auth.json", json.dumps(_make_auth_json("live", "live@example.com")))},
        )
        assert imported.status_code == 200, imported.text
        account = imported.json()["accountId"]
        key = client.post("/api/api-keys/", json={"name": "live-access"}).json()
        headers = {"Authorization": f"Bearer {key['key']}"}
        assert client.put("/api/settings", json={"apiKeyAuthEnabled": True}).status_code == 200
        access_path = f"/api/accounts/{account}/api-key-access"
        assert client.put(access_path, json={"restricted": True, "apiKeyIds": [key["id"]]}).status_code == 200
        created = client.post(
            "/backend-api/codex/realtime/calls",
            content=b"v=offer\r\n",
            headers={**headers, "content-type": "application/sdp"},
        )
        assert created.status_code == 201, created.text
        released.clear()
        with client.websocket_connect(path, headers=headers) as ws:
            send = ws.send_bytes if binary else ws.send_text
            send(b"first" if binary else "first")
            assert ws.receive_text() == "accepted"
            assert client.put(access_path, json={"restricted": True, "apiKeyIds": []}).status_code == 200
            send(b"forbidden" if binary else "forbidden")
            closed = ws.receive()
            assert closed["type"] == "websocket.close"
            assert len(upstream.frames) == 1
        assert upstream.closed.wait(timeout=2)
        assert released.wait(timeout=2)
        with pytest.raises(WebSocketDenialResponse) as denied:
            with client.websocket_connect(path, headers=headers):
                pass
        assert denied.value.status_code == 404
        assert len(connections) == 1
        accounts = client.get("/api/accounts").json()["accounts"]
        assert next(a for a in accounts if a["accountId"] == account)["status"] == "active"
