from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from aiohttp import web
from sqlalchemy import select

from app.core.openai.model_refresh_scheduler import build_model_refresh_scheduler
from app.db.models import ModelSourceModel
from app.db.session import SessionLocal
from app.modules.model_sources import discovery
from app.modules.model_sources.repository import ModelSourcesRepository
from tests.integration.test_model_source_routing import source_upstream  # noqa: F401

pytestmark = pytest.mark.integration


async def _create(client, base_url, **fields):
    response = await client.post("/api/model-sources/", json={"name": "Automatic", "baseUrl": base_url, **fields})
    assert response.status_code == 200
    return response.json()


async def _read(client, source_id):
    response = await client.get("/api/model-sources/")
    assert response.status_code == 200
    return next(row for row in response.json()["sources"] if row["id"] == source_id)


@pytest.mark.asyncio
async def test_discovery_lifecycle_metadata_and_access(async_client, source_upstream):  # noqa: F811
    calls = []
    catalog = {
        "data": [
            {
                "id": "auto-local",
                "display_name": "Provider label",
                "description": "Provider description",
                "context_window": 16384,
                "max_output_tokens": 2048,
                "supports_tools": True,
                "supports_vision": True,
                "supports_reasoning": True,
                "supported_reasoning_levels": ["low", "high"],
                "default_reasoning_level": "high",
                "pricing": {"input_per_1m": 2, "output_per_1m": 4},
                "source_id": "internal",
                "source_request_overrides": {"temperature": 0},
            }
        ]
    }

    async def upstream(request):
        calls.append((request.path, request.headers.get("Authorization")))
        if request.path == "/v1/models":
            return web.json_response(catalog)
        return web.json_response(
            {
                "id": "chat_auto",
                "model": "auto-local",
                "choices": [],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        )

    base_url = await source_upstream(upstream)
    selected = (await async_client.post("/api/api-keys/", json={"name": "Selected"})).json()
    other = (await async_client.post("/api/api-keys/", json={"name": "Other"})).json()
    source = await _create(async_client, base_url + "/", apiKey="stub-provider-key", allowedApiKeyIds=[selected["id"]])
    source_id = source["id"]
    assert source["autoDiscoverModels"] and source["models"] == []
    # Test environment disables subscription registry and has no accounts:
    # production scheduler still runs the source discovery pass.
    await build_model_refresh_scheduler()._refresh_once()
    fetched = await _read(async_client, source_id)
    assert fetched["autoDiscoverModels"]
    model = fetched["models"][0]
    assert model["displayName"] == "Provider label" and model["contextWindow"] == 16384
    assert model["maxOutputTokens"] == 2048 and model["supportsTools"] and model["supportsVision"]
    assert model["inputPer1M"] == 2 and model["outputPer1M"] == 4
    assert calls == [("/v1/models", "Bearer stub-provider-key")]
    assert not fetched["supportsResponses"] and not fetched["supportsEmbeddings"]
    renamed = await async_client.patch(f"/api/model-sources/{source_id}", json={"name": "Renamed"})
    assert renamed.json()["autoDiscoverModels"] and renamed.json()["models"] == fetched["models"]
    await async_client.put("/api/settings", json={"apiKeyAuthEnabled": True})
    for key in (selected, other):
        headers = {"Authorization": f"Bearer {key['key']}"}
        listed = (await async_client.get("/v1/models", headers=headers)).json()["data"]
        entry = next((item for item in listed if item["id"] == "auto-local"), None)
        assert (entry is not None) == (key == selected)
        if entry:
            assert entry["metadata"]["description"] == "Provider description"
            assert entry["metadata"]["default_reasoning_level"] == "high"
            assert source_id not in str(entry) and "source_request_overrides" not in str(entry)
        dispatched_before = len(calls)
        result = await async_client.post(
            "/v1/chat/completions",
            headers=headers,
            json={"model": "auto-local", "messages": [{"role": "user", "content": "Hi"}]},
        )
        assert result.status_code == (200 if key == selected else 503)
        assert len(calls) == dispatched_before + (1 if key == selected else 0)
    # Surviving row IDs/disable flags survive refresh; authoritative removal works.
    async with SessionLocal() as session:
        row = await session.get(ModelSourceModel, model["id"])
        assert row is not None
        row.is_enabled = False
        await session.commit()
    catalog["data"][0]["context_window"] = 32768
    await discovery.refresh_source_catalogs()
    refreshed = await _read(async_client, source_id)
    assert refreshed["models"][0]["id"] == model["id"]
    assert not refreshed["models"][0]["isEnabled"]
    assert refreshed["models"][0]["contextWindow"] == 32768
    # Nonempty -> manual; clear -> auto retaining last known rows; null/omitted preserve.
    manual = await async_client.patch(f"/api/model-sources/{source_id}", json={"models": [{"model": "manual"}]})
    assert not manual.json()["autoDiscoverModels"]
    before = len(calls)
    await discovery.refresh_source_catalogs()
    assert len(calls) == before
    auto = await async_client.patch(f"/api/model-sources/{source_id}", json={"models": []})
    assert auto.json()["autoDiscoverModels"] and auto.json()["models"][0]["model"] == "manual"
    preserved = await async_client.patch(f"/api/model-sources/{source_id}", json={"models": None})
    assert preserved.json()["models"] == auto.json()["models"]
    catalog["data"] = []
    await discovery.refresh_source_catalogs()
    empty = await _read(async_client, source_id)
    assert empty["autoDiscoverModels"] and empty["models"] == []


@pytest.mark.asyncio
async def test_failed_catalogs_and_writes_preserve_cache_and_do_not_block_peers(
    async_client,
    source_upstream,  # noqa: F811
    monkeypatch,
):  # noqa: F811
    status = 200
    catalog = {"data": [{"id": "stable"}]}

    async def upstream(request):
        return web.json_response(catalog, status=status)

    base_url = await source_upstream(upstream)
    source = await _create(async_client, base_url)
    await discovery.refresh_source_catalogs()
    good = (await _read(async_client, source["id"]))["models"]
    for failure in (401, 500, 200):
        status = failure
        catalog = {"data": [{"id": "new"}, {"id": " "}]}
        await discovery.refresh_source_catalogs()
        assert (await _read(async_client, source["id"]))["models"] == good
    real_apply = ModelSourcesRepository.apply_discovered_models
    status = 200
    catalog = {"data": [{"id": "changed"}]}

    async def fail_commit(repository, *args):
        repository._session.commit = AsyncMock(side_effect=RuntimeError("Stub commit failure"))
        return await real_apply(repository, *args)

    monkeypatch.setattr(ModelSourcesRepository, "apply_discovered_models", fail_commit)
    await discovery.refresh_source_catalogs()
    assert (await _read(async_client, source["id"]))["models"] == good
    monkeypatch.setattr(ModelSourcesRepository, "apply_discovered_models", real_apply)
    peer = await _create(async_client, base_url, name="Peer")
    real_fetch = discovery.fetch_source_catalog

    async def one_failure(row):
        if row.id == source["id"]:
            raise ConnectionError("Stub transport failure")
        return await real_fetch(row)

    monkeypatch.setattr(discovery, "fetch_source_catalog", one_failure)
    await discovery.refresh_source_catalogs()
    assert (await _read(async_client, source["id"]))["models"] == good
    assert (await _read(async_client, peer["id"]))["models"][0]["model"] == "changed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "edit",
    [
        {"models": [{"model": "manual"}]},
        {"baseUrl": "http://127.0.0.1:9/v1"},
        {"apiKey": "new-stub-key"},
        {"isEnabled": False},
        {"name": "Renamed"},
        "delete",
        "disable-enable",
    ],
)
async def test_inflight_discovery_does_not_overwrite_operator_edits(async_client, monkeypatch, edit):
    source = await _create(async_client, "http://127.0.0.1:9/v1")
    entered, release = asyncio.Event(), asyncio.Event()

    async def fetch(row):
        entered.set()
        await release.wait()
        return discovery.parse_source_catalog(b'{"data": [{"id": "stale"}]}')

    monkeypatch.setattr(discovery, "fetch_source_catalog", fetch)
    task = asyncio.create_task(discovery.refresh_source_catalogs())
    try:
        await asyncio.wait_for(entered.wait(), 1)
        path = f"/api/model-sources/{source['id']}"
        if edit == "delete":
            assert (await async_client.delete(path)).status_code == 204
        elif edit == "disable-enable":
            await async_client.patch(path, json={"isEnabled": False})
            await async_client.patch(path, json={"isEnabled": True})
        else:
            assert (await async_client.patch(path, json=edit)).status_code == 200
        release.set()
        await asyncio.wait_for(task, 1)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
    async with SessionLocal() as session:
        rows = (
            await session.execute(select(ModelSourceModel).where(ModelSourceModel.source_id == source["id"]))
        ).scalars()
        assert [row.model for row in rows] == (["manual"] if isinstance(edit, dict) and "models" in edit else [])


@pytest.mark.asyncio
async def test_discovery_shutdown_cancels_without_writes(async_client, monkeypatch):
    source = await _create(async_client, "http://127.0.0.1:9/v1")
    entered, cancelled = asyncio.Event(), asyncio.Event()

    async def fetch(row):
        entered.set()
        try:
            await asyncio.Future()
        finally:
            cancelled.set()

    monkeypatch.setattr(discovery, "fetch_source_catalog", fetch)
    task = asyncio.create_task(discovery.refresh_source_catalogs())
    await asyncio.wait_for(entered.wait(), 1)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert cancelled.is_set() and (await _read(async_client, source["id"]))["models"] == []


@pytest.mark.asyncio
async def test_catalog_fetch_bounds_timeout_and_skips_disabled_sources(
    async_client,
    source_upstream,  # noqa: F811
    monkeypatch,
):  # noqa: F811
    delay = 0
    catalog = {"data": [{"id": "cached"}]}
    calls = 0

    async def upstream(request):
        nonlocal calls
        calls += 1
        await asyncio.sleep(delay)
        return web.json_response(catalog)

    source = await _create(async_client, await source_upstream(upstream))
    await discovery.refresh_source_catalogs()
    cached = (await _read(async_client, source["id"]))["models"]
    catalog = {"data": [{"id": "oversized-" * 20}]}
    monkeypatch.setattr(discovery, "_MAX_CATALOG_BYTES", 64)
    await discovery.refresh_source_catalogs()
    assert (await _read(async_client, source["id"]))["models"] == cached
    monkeypatch.setattr(discovery, "_MAX_CATALOG_BYTES", 4 * 1024 * 1024)
    monkeypatch.setattr(discovery, "_MAX_FETCH_SECONDS", 0.01)
    delay = 0.1
    await discovery.refresh_source_catalogs()
    assert (await _read(async_client, source["id"]))["models"] == cached
    await async_client.patch(f"/api/model-sources/{source['id']}", json={"isEnabled": False})
    before = calls
    await discovery.refresh_source_catalogs()
    assert calls == before
