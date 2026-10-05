from __future__ import annotations

import pytest
from aiohttp import web

from app.db.session import SessionLocal
from app.modules.api_keys.repository import ApiKeysRepository
from app.modules.api_keys.service import ApiKeysService
from app.modules.model_sources.selection import responses_model_is_source_owned
from tests.integration.test_model_source_routing import source_upstream  # noqa: F401

pytestmark = pytest.mark.integration
MODEL = "private-source-model"


async def _key(client, name):
    response = await client.post("/api/api-keys/", json={"name": name})
    assert response.status_code == 200
    return response.json()


async def _headers(client, key):
    settings = await client.put("/api/settings", json={"apiKeyAuthEnabled": key is not None})
    assert settings.status_code == 200
    return {"Authorization": f"Bearer {key['key']}"} if key else {}


async def _source(client, ids, *, name="Private", base_url="http://127.0.0.1:9/v1", model=MODEL):
    response = await client.post(
        "/api/model-sources/",
        json={
            "name": name,
            "baseUrl": base_url,
            "allowedApiKeyIds": ids,
            "supportsResponses": True,
            "supportsAudioTranscriptions": True,
            "supportsEmbeddings": True,
            "models": [{"model": model}],
        },
    )
    assert response.status_code == 200
    return response.json()


async def _listed_source(client, source_id):
    response = await client.get("/api/model-sources/")
    assert response.status_code == 200
    return next(source for source in response.json()["sources"] if source["id"] == source_id)


@pytest.mark.asyncio
async def test_source_whitelist_lifecycle_and_catalogs(async_client):
    selected = await _key(async_client, "Selected")
    other = await _key(async_client, "Other")
    source = await _source(async_client, [selected["id"], selected["id"]])
    source_id = source["id"]
    assert source["allowedApiKeyIds"] == [selected["id"]]
    path = f"/api/model-sources/{source_id}"

    for caller in (selected, other, None):
        for catalog in ("/v1/models", "/backend-api/codex/models"):
            response = await async_client.get(catalog, headers=await _headers(async_client, caller))
            assert response.status_code == 200
            models = response.json().get("data", response.json().get("models", []))
            assert any(row.get("id", row.get("slug")) == MODEL for row in models) == (caller == selected)
            assert "allowedApiKeyIds" not in response.text
            assert source_id not in response.text

    async with SessionLocal() as session:
        service = ApiKeysService(ApiKeysRepository(session))
        selected_data = await service.validate_key(selected["key"])
        other_data = await service.validate_key(other["key"])
    assert await responses_model_is_source_owned(MODEL, selected_data)
    assert not await responses_model_is_source_owned(MODEL, other_data)
    assert not await responses_model_is_source_owned(MODEL, None)

    for invalid in (["missing"], [""], [None], None, "wrong-shape"):
        response = await async_client.patch(path, json={"name": "Should not save", "allowedApiKeyIds": invalid})
        assert response.status_code in (400, 422)
        assert (await _listed_source(async_client, source_id)) == source
    response = await async_client.post(
        "/api/model-sources/",
        json={"name": "Invalid", "baseUrl": "http://localhost/v1", "allowedApiKeyIds": ["missing"]},
    )
    assert response.status_code == 400

    renamed = await async_client.patch(path, json={"name": "Renamed"})
    assert renamed.status_code == 200
    assert renamed.json()["allowedApiKeyIds"] == [selected["id"]]
    regenerated = await async_client.post(f"/api/api-keys/{selected['id']}/regenerate")
    assert regenerated.status_code == 200
    assert (await _listed_source(async_client, source_id))["allowedApiKeyIds"] == [selected["id"]]
    assert (await async_client.delete(f"/api/api-keys/{selected['id']}")).status_code == 204
    assert (await _listed_source(async_client, source_id))["allowedApiKeyIds"] == [selected["id"]]
    # An unrelated edit can retain a key that has since disappeared.
    retained = await async_client.patch(path, json={"allowedApiKeyIds": [selected["id"]], "name": "Retained"})
    assert retained.status_code == 200
    models = (await async_client.get("/v1/models", headers=await _headers(async_client, other))).json()["data"]
    assert MODEL not in {row["id"] for row in models}

    cleared = await async_client.patch(path, json={"allowedApiKeyIds": []})
    assert cleared.status_code == 200
    assert cleared.json()["allowedApiKeyIds"] == []
    assert await responses_model_is_source_owned(MODEL, None)
    for caller in (other, None):
        models = (await async_client.get("/v1/models", headers=await _headers(async_client, caller))).json()["data"]
        assert MODEL in {row["id"] for row in models}


@pytest.mark.asyncio
async def test_source_whitelist_omission_defaults_to_shared(async_client):
    response = await async_client.post(
        "/api/model-sources/", json={"name": "Default", "baseUrl": "http://localhost/v1", "models": [{"model": MODEL}]}
    )
    assert response.status_code == 200
    assert response.json()["allowedApiKeyIds"] == []
    assert (await _listed_source(async_client, response.json()["id"]))["allowedApiKeyIds"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "route",
    [
        "/v1/chat/completions",
        "/v1/responses",
        "/backend-api/codex/responses",
        "/v1/audio/transcriptions",
        "/v1/embeddings",
    ],
)
async def test_source_whitelist_routes_all_capabilities(async_client, source_upstream, route):  # noqa: F811
    selected = await _key(async_client, "Selected")
    other = await _key(async_client, "Other")
    calls = []

    async def upstream(request):
        calls.append(request.path)
        usage = {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3}
        if request.path.endswith("/audio/transcriptions"):
            return web.json_response({"text": "ok", "usage": usage})
        if request.path.endswith("/embeddings"):
            return web.json_response({"object": "list", "data": [], "model": MODEL, "usage": usage})
        if request.path.endswith("/responses"):
            return web.json_response(
                {
                    "id": "resp_whitelist",
                    "object": "response",
                    "status": "completed",
                    "model": MODEL,
                    "output": [],
                    "usage": {"input_tokens": 2, "output_tokens": 1, "total_tokens": 3},
                }
            )
        return web.json_response(
            {
                "id": "chatcmpl_whitelist",
                "object": "chat.completion",
                "created": 1,
                "model": MODEL,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
                "usage": usage,
            }
        )

    base_url = await source_upstream(upstream)
    source = await _source(async_client, [selected["id"]], base_url=base_url)

    async def request(caller):
        if route.endswith("/audio/transcriptions"):
            return await async_client.post(
                route,
                headers=await _headers(async_client, caller),
                files={"model": (None, MODEL), "file": ("sample.wav", b"audio", "audio/wav")},
            )
        if route.endswith("/chat/completions"):
            payload = {"model": MODEL, "messages": [{"role": "user", "content": "hi"}]}
        else:
            payload = {"model": MODEL, "input": "hi", "stream": False}
        return await async_client.post(route, headers=await _headers(async_client, caller), json=payload)

    for caller in (selected, other, None):
        before = len(calls)
        response = await request(caller)
        if caller == selected:
            assert response.status_code == 200, response.text
            assert len(calls) == before + 1
        else:
            assert response.status_code >= 400
            assert len(calls) == before

    # Per-key assignments must intersect with the source whitelist.
    unrelated = await _source(async_client, [], name="Unrelated", model="unrelated-source-model")
    excluded = await async_client.patch(
        f"/api/api-keys/{selected['id']}", json={"assignedSourceIds": [unrelated["id"]]}
    )
    assert excluded.status_code == 200
    assert excluded.json()["sourceAssignmentScopeEnabled"] is True
    before = len(calls)
    assert (await request(selected)).status_code >= 400
    assert len(calls) == before
    models = (await async_client.get("/v1/models", headers=await _headers(async_client, selected))).json()["data"]
    assert MODEL not in {row["id"] for row in models}

    # A later permitted source must not be hidden by the earlier restricted one.
    await _source(async_client, [], name="Z Shared", base_url=base_url)
    for caller in (other, None):
        before = len(calls)
        response = await request(caller)
        assert response.status_code == 200, response.text
        assert len(calls) == before + 1

    # Clearing the source selection restores all callers, even with its key gone.
    clear = await async_client.patch(f"/api/model-sources/{source['id']}", json={"allowedApiKeyIds": []})
    assert clear.status_code == 200
    for caller in (other, None):
        assert (await request(caller)).status_code == 200
