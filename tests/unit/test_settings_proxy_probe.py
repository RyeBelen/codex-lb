from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

import app.modules.settings.api as settings_api
from app.core.upstream_proxy import ResolvedProxyEndpoint

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_http_probe_sends_basic_auth_on_connect() -> None:
    heads: list[bytes] = []

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        heads.append(await reader.readuntil(b"\r\n\r\n"))
        writer.write(b"HTTP/1.1 407 Proxy Authentication Required\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()
        writer.close()

    server = await asyncio.start_server(handle, "127.0.0.1", 0)
    try:
        port = server.sockets[0].getsockname()[1]
        endpoint = ResolvedProxyEndpoint("probe", "http", "127.0.0.1", port, "u", "p")
        with pytest.raises(httpx.ProxyError):
            await settings_api._probe_upstream_proxy_endpoint(endpoint)
    finally:
        server.close()
        await server.wait_closed()

    assert heads[0].startswith(b"CONNECT chatgpt.com:443 HTTP/1.1\r\n")
    assert b"proxy-authorization: basic dtpw\r\n" in heads[0].lower()


@pytest.mark.asyncio
async def test_socks_probe_uses_shared_ssl_context() -> None:
    endpoint = SimpleNamespace(
        scheme="socks5h",
        host="proxy.test",
        port=1080,
        username=None,
        password=None,
        proxy_url="socks5h://proxy.test:1080",
    )
    shared_context = MagicMock()
    session = MagicMock()
    session.__aenter__.return_value = session
    session.get = AsyncMock(return_value=SimpleNamespace(status=204))

    with (
        patch("app.modules.settings.api._shared_ssl_context", return_value=shared_context) as shared_factory,
        patch("app.modules.settings.api.ProxyConnector") as proxy_connector_cls,
        patch("app.modules.settings.api.aiohttp.ClientSession", return_value=session),
    ):
        status = await settings_api._probe_upstream_proxy_endpoint(endpoint)

    assert status == 204
    shared_factory.assert_called_once_with()
    assert proxy_connector_cls.call_args.kwargs["ssl"] is shared_context
    assert proxy_connector_cls.call_args.kwargs["rdns"] is True
