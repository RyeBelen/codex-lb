from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import cast

import pytest
from starlette.requests import Request

import app.core.auth.dependencies as auth_dependencies
from app.modules.api_keys.service import ApiKeyData, ApiKeysRepositoryProtocol, ApiKeysService


def _api_key(*, remaining: int = 1) -> ApiKeyData:
    return ApiKeyData(
        id="key-verbose",
        name="Verbose key",
        key_prefix="sk-clb-test",
        allowed_models=None,
        enforced_model=None,
        enforced_reasoning_effort=None,
        enforced_service_tier=None,
        expires_at=None,
        is_active=True,
        created_at=datetime(2026, 8, 24),
        last_used_at=None,
        verbose_capture_remaining=remaining,
    )


def _request(*, body: bytes, content_type: str = "application/json") -> Request:
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/responses",
            "raw_path": b"/v1/responses",
            "query_string": b"",
            "headers": [(b"content-type", content_type.encode())],
            "client": ("127.0.0.1", 1234),
            "server": ("test", 80),
            "scheme": "http",
        },
        receive,
    )


@pytest.mark.asyncio
async def test_json_proxy_request_is_eligible_for_verbose_capture(monkeypatch):
    captures: list[dict] = []

    class FakeService:
        def __init__(self, repository) -> None:
            del repository

        async def capture_verbose_request(self, **kwargs) -> bool:
            captures.append(kwargs)
            return True

    @asynccontextmanager
    async def fake_session():
        yield object()

    monkeypatch.setattr(auth_dependencies, "ApiKeysService", FakeService)
    monkeypatch.setattr(auth_dependencies, "ApiKeysRepository", lambda session: session)
    monkeypatch.setattr(auth_dependencies, "get_background_session", fake_session)

    request = _request(body=b'{"input":"hello"}', content_type="application/vnd.api+json; charset=utf-8")
    await auth_dependencies._capture_verbose_request_if_eligible(request, _api_key())

    assert len(captures) == 1
    assert captures[0]["body"] == b'{"input":"hello"}'
    assert captures[0]["method"] == "POST"
    assert captures[0]["path"] == "/v1/responses"
    assert "headers" not in captures[0]


@pytest.mark.asyncio
async def test_cached_zero_budget_still_checks_authoritative_database_counter(monkeypatch):
    captures: list[dict] = []

    class FakeService:
        def __init__(self, repository) -> None:
            del repository

        async def capture_verbose_request(self, **kwargs) -> bool:
            captures.append(kwargs)
            return True

    @asynccontextmanager
    async def fake_session():
        yield object()

    monkeypatch.setattr(auth_dependencies, "ApiKeysService", FakeService)
    monkeypatch.setattr(auth_dependencies, "ApiKeysRepository", lambda session: session)
    monkeypatch.setattr(auth_dependencies, "get_background_session", fake_session)

    await auth_dependencies._capture_verbose_request_if_eligible(
        _request(body=b"{}"),
        _api_key(remaining=0),
    )

    assert len(captures) == 1


@pytest.mark.asyncio
async def test_service_does_not_treat_cached_zero_as_authoritative():
    calls: list[dict] = []

    class FakeRepository:
        async def try_capture_verbose_request(self, **kwargs) -> int:
            calls.append(kwargs)
            return 1

    service = ApiKeysService(cast(ApiKeysRepositoryProtocol, FakeRepository()))
    captured = await service.capture_verbose_request(
        api_key=_api_key(remaining=0),
        request_id="req-stale-cache",
        method="POST",
        path="/v1/responses",
        content_type="application/json",
        body=b"{}",
    )

    assert captured is True
    assert len(calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("remaining", "content_type", "body"),
    [
        (1, "multipart/form-data; boundary=test", b"--test"),
        (1, "application/json", b""),
        (1, "text/plain", b"{}"),
    ],
)
async def test_ineligible_proxy_requests_do_not_open_capture_session(
    monkeypatch,
    remaining: int,
    content_type: str,
    body: bytes,
):
    opened = False

    @asynccontextmanager
    async def fake_session():
        nonlocal opened
        opened = True
        yield object()

    monkeypatch.setattr(auth_dependencies, "get_background_session", fake_session)

    await auth_dependencies._capture_verbose_request_if_eligible(
        _request(body=body, content_type=content_type),
        _api_key(remaining=remaining),
    )

    assert opened is False
