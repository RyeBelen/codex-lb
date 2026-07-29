from __future__ import annotations

import asyncio
import contextlib
import socket
from collections.abc import AsyncIterator
from typing import cast

import pytest
import uvicorn
from starlette.types import Receive, Scope, Send
from websockets.legacy.client import WebSocketClientProtocol, connect
from websockets.typing import DataLike

pytestmark = pytest.mark.integration


async def _pending_turn_websocket(scope: Scope, receive: Receive, send: Send) -> None:
    assert scope["type"] == "websocket"
    await send({"type": "websocket.accept"})
    request_pending = False
    while True:
        message = await receive()
        if message["type"] == "websocket.disconnect":
            return
        if message["type"] == "websocket.receive":
            if message.get("text") == "response.create":
                request_pending = True
                await send({"type": "websocket.send", "text": "response.created"})
            elif message.get("text") == "complete" and request_pending:
                request_pending = False
                await send({"type": "websocket.send", "text": "response.completed"})


class _NoPongClientProtocol(WebSocketClientProtocol):
    suppress_pongs = True
    suppressed_pong_payloads: list[DataLike] = []

    async def pong(self, data: DataLike = b"") -> None:
        if type(self).suppress_pongs:
            type(self).suppressed_pong_payloads.append(data)
            return
        await super().pong(data)

    async def release_suppressed_pongs(self) -> None:
        type(self).suppress_pongs = False
        payloads = type(self).suppressed_pong_payloads
        type(self).suppressed_pong_payloads = []
        for payload in payloads:
            await super().pong(payload)


@contextlib.asynccontextmanager
async def _serve_with_ping_timeout(
    *,
    ping_interval: float,
    ping_timeout: float | None,
) -> AsyncIterator[int]:
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen()
    port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(
            _pending_turn_websocket,
            ws="websockets",
            lifespan="off",
            log_level="warning",
            ws_ping_interval=ping_interval,
            ws_ping_timeout=ping_timeout,
        )
    )
    server_task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(5):
            while not server.started:
                if server_task.done():
                    await server_task
                await asyncio.sleep(0.01)
        yield port
    finally:
        server.should_exit = True
        try:
            async with asyncio.timeout(5):
                await server_task
        finally:
            listener.close()


@pytest.mark.asyncio
async def test_server_without_pong_timeout_keeps_non_ponging_client_connected() -> None:
    _NoPongClientProtocol.suppress_pongs = True
    _NoPongClientProtocol.suppressed_pong_payloads = []

    async with _serve_with_ping_timeout(ping_interval=0.05, ping_timeout=None) as port:
        async with connect(
            f"ws://127.0.0.1:{port}/ws",
            create_protocol=_NoPongClientProtocol,
            ping_interval=None,
            close_timeout=0.2,
        ) as websocket:
            no_pong_websocket = cast(_NoPongClientProtocol, websocket)
            await websocket.send("response.create")
            assert await websocket.recv() == "response.created"

            await asyncio.sleep(0.25)

            assert _NoPongClientProtocol.suppressed_pong_payloads
            assert not websocket.closed
            await websocket.send("complete")
            assert await websocket.recv() == "response.completed"
            await no_pong_websocket.release_suppressed_pongs()
            await asyncio.sleep(0.05)
