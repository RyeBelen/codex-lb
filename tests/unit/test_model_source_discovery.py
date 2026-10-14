from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.openai import model_refresh_scheduler as scheduler_module
from app.modules.model_sources.discovery import parse_source_catalog

pytestmark = pytest.mark.unit


def test_catalog_maps_advertised_metadata_and_drops_internal_controls():
    body = json.dumps(
        {
            "data": [
                {
                    "id": "z",
                    "context_length": 8192,
                    "supports_streaming": False,
                    "metadata": {
                        "display_name": "Remote",
                        "description": "Advertised description",
                        "input_modalities": ["text", "image"],
                        "supported_reasoning_levels": [{"effort": "high", "description": "Deep"}],
                        "default_reasoning_level": "high",
                        "source_id": "secret-source",
                        "source_request_overrides": {"temperature": 0},
                    },
                    "capabilities": {"supports_parallel_tool_calls": True},
                    "pricing": {
                        "input_per_1m": 1.5,
                        "cached_input_per_1m": 0.2,
                        "output_per_1m": 3,
                        "audio_per_minute": 0.01,
                    },
                    "api_key": "never-import",
                    "is_enabled": False,
                    "raw_metadata_json": '{"source_request_overrides": {"temperature": 1}}',
                },
                {"id": "a"},
                {"id": "z", "context_window": 9999},
            ]
        }
    ).encode()
    models = parse_source_catalog(body)
    assert [model.model for model in models] == ["a", "z"]
    basic, rich = models
    assert basic.context_window is None and basic.input_per_1m is None
    assert basic.supports_tools is False and basic.supports_vision is False
    assert rich.display_name == "Remote" and rich.context_window == 8192
    assert rich.supports_streaming is False and rich.supports_tools and rich.supports_vision
    assert rich.input_per_1m == 1.5 and rich.output_per_1m == 3 and rich.audio_per_minute == 0.01
    assert rich.is_enabled
    assert rich.raw_metadata_json is not None
    raw = json.loads(rich.raw_metadata_json)
    assert raw["description"] == "Advertised description" and raw["supports_reasoning"] is True
    for key in ("source_id", "api_key", "source_request_overrides", "raw_metadata_json", "is_enabled"):
        assert key not in raw


@pytest.mark.parametrize(
    "invalid",
    [
        {},
        {"data": None},
        {"data": {}},
        {"data": [{"id": "ok"}, {"id": " "}]},
        {"data": [{"id": 123}]},
        {"data": [{"id": "x", "context_window": True}]},
        {"data": [{"id": "x", "supports_tools": "true"}]},
        {"data": [{"id": "x", "output_per_1m": -1}]},
        {"data": [{"id": "x", "pricing": {"input_per_1m": float("inf")}}]},
        {"data": [{"id": "x", "supported_reasoning_levels": [{}]}]},
    ],
)
def test_catalog_rejects_entire_malformed_response(invalid):
    with pytest.raises(ValueError):
        parse_source_catalog(json.dumps(invalid).encode())


def test_catalog_bounds_and_empty_list(monkeypatch):
    import app.modules.model_sources.discovery as discovery

    assert parse_source_catalog(b'{"data": []}') == []
    with pytest.raises(ValueError):
        parse_source_catalog(json.dumps({"data": [{"id": "x"}] * 10_001}).encode())
    monkeypatch.setattr(discovery, "_MAX_CATALOG_BYTES", 3)
    with pytest.raises(ValueError, match="size limit"):
        parse_source_catalog(b'{"data": []}')


@pytest.mark.asyncio
async def test_scheduler_discovery_runs_without_subscription_registry_and_on_each_tick(monkeypatch):
    refresh = AsyncMock()
    subscription = AsyncMock()

    class Leader:
        async def run_if_leader(self, fn):
            return await fn()

    monkeypatch.setattr(scheduler_module, "get_settings", lambda: SimpleNamespace(model_registry_enabled=False))
    monkeypatch.setattr(scheduler_module, "refresh_source_catalogs", refresh)
    monkeypatch.setattr(scheduler_module, "AccountsRepository", subscription)
    monkeypatch.setattr(scheduler_module, "_get_leader_election", Leader)
    scheduler = scheduler_module.build_model_refresh_scheduler()
    assert scheduler.enabled and scheduler.interval_seconds == 300
    monkeypatch.setattr(scheduler, "interval_seconds", 0.01)
    await scheduler.start()
    try:
        async with asyncio.timeout(1):
            while refresh.await_count < 2:
                await asyncio.sleep(0)
    finally:
        await scheduler.stop()
    assert scheduler._task is None
    subscription.assert_not_called()


@pytest.mark.asyncio
async def test_scheduler_follower_does_not_fetch_and_stop_cancels_fetch(monkeypatch):
    entered = asyncio.Event()
    cancelled = asyncio.Event()

    async def refresh():
        entered.set()
        try:
            await asyncio.Future()
        finally:
            cancelled.set()

    class Leader:
        leader = False

        async def run_if_leader(self, fn):
            return await fn() if self.leader else None

    leader = Leader()
    monkeypatch.setattr(scheduler_module, "_get_leader_election", lambda: leader)
    monkeypatch.setattr(scheduler_module, "refresh_source_catalogs", refresh)
    scheduler = scheduler_module.ModelRefreshScheduler(300, True, refresh_subscription_models=False)
    await scheduler._refresh_once()
    assert not entered.is_set()
    leader.leader = True
    await scheduler.start()
    await asyncio.wait_for(entered.wait(), 1)
    await scheduler.stop()
    assert cancelled.is_set() and scheduler._task is None


@pytest.mark.asyncio
async def test_scheduler_lease_loss_cancels_source_refresh(monkeypatch):
    from tests.unit.test_leader_election import _FakeSession, _install, leader_election_module

    _install(monkeypatch, _FakeSession("postgresql", [1, 0]), ttl=3)
    leader = leader_election_module.LeaderElection(leader_id="source-leader")
    cancelled = asyncio.Event()

    async def refresh():
        try:
            await asyncio.Future()
        finally:
            cancelled.set()

    monkeypatch.setattr(scheduler_module, "_get_leader_election", lambda: leader)
    monkeypatch.setattr(scheduler_module, "refresh_source_catalogs", refresh)
    scheduler = scheduler_module.ModelRefreshScheduler(300, True, refresh_subscription_models=False)
    async with asyncio.timeout(4):
        await scheduler._refresh_once()
    assert cancelled.is_set() and not leader.is_leader
