from __future__ import annotations

import asyncio
import json

import pytest
from anyio import to_thread
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.migrate import _build_alembic_config, run_upgrade
from app.db.models import ApiKey, ApiKeyVerboseCapture, AuditLog
from app.db.session import SessionLocal
from app.modules.api_keys.repository import ApiKeysRepository
from app.modules.api_keys.service import (
    VERBOSE_CAPTURE_MAX_PAYLOAD_BYTES,
    ApiKeysService,
)
from app.modules.request_logs.repository import RequestLogsRepository

pytestmark = pytest.mark.integration


async def _wait_for_audit_log(
    action: str,
    *,
    details: dict[str, object] | None = None,
    attempts: int = 20,
) -> AuditLog:
    for _ in range(attempts):
        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(AuditLog).where(AuditLog.action == action).order_by(AuditLog.id.desc())
                )
            ).scalars()
            for row in rows:
                if details is None or json.loads(row.details or "{}") == details:
                    return row
        await asyncio.sleep(0.05)
    raise AssertionError(f"audit log not written for action={action}")


@pytest.mark.asyncio
async def test_verbose_capture_budget_is_configurable_and_can_be_disabled(async_client):
    created = await async_client.post("/api/api-keys/", json={"name": "verbose-key"})
    assert created.status_code == 200
    key_id = created.json()["id"]
    assert created.json()["verboseCaptureRemaining"] == 0

    too_small = await async_client.post(
        f"/api/api-keys/{key_id}/verbose-capture",
        json={"requestCount": 0},
    )
    too_large = await async_client.post(
        f"/api/api-keys/{key_id}/verbose-capture",
        json={"requestCount": 101},
    )
    assert too_small.status_code == 422
    assert too_large.status_code == 422

    armed = await async_client.post(
        f"/api/api-keys/{key_id}/verbose-capture",
        json={"requestCount": 7},
    )
    assert armed.status_code == 200
    assert armed.json()["verboseCaptureRemaining"] == 7

    replaced = await async_client.post(
        f"/api/api-keys/{key_id}/verbose-capture",
        json={"requestCount": 20},
    )
    assert replaced.status_code == 200
    assert replaced.json()["verboseCaptureRemaining"] == 20
    invalid_replacement = await async_client.post(
        f"/api/api-keys/{key_id}/verbose-capture",
        json={"requestCount": 0},
    )
    assert invalid_replacement.status_code == 422
    listed = await async_client.get("/api/api-keys/")
    assert listed.json()[0]["verboseCaptureRemaining"] == 20

    expected_audit_details = {"key_id": key_id, "request_count": 20}
    audit_log = await _wait_for_audit_log(
        "api_key_verbose_capture_enabled",
        details=expected_audit_details,
    )
    assert json.loads(audit_log.details or "{}") == expected_audit_details
    assert "payload" not in (audit_log.details or "")

    disabled = await async_client.delete(f"/api/api-keys/{key_id}/verbose-capture")
    assert disabled.status_code == 200
    assert disabled.json()["verboseCaptureRemaining"] == 0


@pytest.mark.asyncio
async def test_verbose_capture_is_bounded_idempotent_and_visible_from_request_logs(async_client):
    created = await async_client.post("/api/api-keys/", json={"name": "capture-key"})
    assert created.status_code == 200
    created_payload = created.json()
    key_id = created_payload["id"]
    plain_key = created_payload["key"]

    armed = await async_client.post(
        f"/api/api-keys/{key_id}/verbose-capture",
        json={"requestCount": 2},
    )
    assert armed.status_code == 200

    json_prefix = b'{"input":"'
    oversized_body = (
        json_prefix
        + (b"x" * (VERBOSE_CAPTURE_MAX_PAYLOAD_BYTES - len(json_prefix) - 1))
        + "🙂".encode()
        + b'"}'
    )
    async with SessionLocal() as session:
        service = ApiKeysService(ApiKeysRepository(session))
        api_key = await service.validate_key(plain_key)

        assert await service.capture_verbose_request(
            api_key=api_key,
            request_id="req-capture-1",
            method="POST",
            path="/v1/responses",
            content_type="application/json",
            body=oversized_body,
        )
        assert not await service.capture_verbose_request(
            api_key=api_key,
            request_id="req-capture-1",
            method="POST",
            path="/v1/responses",
            content_type="application/json",
            body=b'{"duplicate":true}',
        )
        assert await service.capture_verbose_request(
            api_key=api_key,
            request_id="req-capture-2",
            method="POST",
            path="/v1/chat/completions",
            content_type="application/problem+json",
            body=b'{"messages":[]}',
        )
        assert not await service.capture_verbose_request(
            api_key=api_key,
            request_id="req-capture-3",
            method="POST",
            path="/v1/responses",
            content_type="application/json",
            body=b'{"input":"not captured"}',
        )

    async with SessionLocal() as session:
        key = await session.get(ApiKey, key_id)
        assert key is not None
        assert key.verbose_capture_remaining == 0
        captures = list(
            (
                await session.execute(
                    select(ApiKeyVerboseCapture)
                    .where(ApiKeyVerboseCapture.api_key_id == key_id)
                    .order_by(ApiKeyVerboseCapture.request_id)
                )
            ).scalars()
        )
        assert [capture.request_id for capture in captures] == ["req-capture-1", "req-capture-2"]
        assert captures[0].truncated is True
        assert len(captures[0].payload.encode("utf-8")) <= VERBOSE_CAPTURE_MAX_PAYLOAD_BYTES
        assert "�" not in captures[0].payload
        assert captures[0].content_type == "application/json"

        log = await RequestLogsRepository(session).add_log(
            account_id=None,
            request_id="req-capture-1",
            model="gpt-test",
            input_tokens=1,
            output_tokens=1,
            latency_ms=10,
            status="success",
            error_code=None,
            api_key_id=key_id,
        )
        request_log_id = log.id

    listed = await async_client.get("/api/request-logs?limit=10")
    assert listed.status_code == 200
    row = next(item for item in listed.json()["requests"] if item["requestId"] == "req-capture-1")
    assert row["requestLogId"] == request_log_id
    assert row["hasCapturedInput"] is True
    assert "payload" not in row

    capture_response = await async_client.get(f"/api/request-logs/{request_log_id}/captured-input")
    assert capture_response.status_code == 200
    assert capture_response.json() == {
        "requestLogId": request_log_id,
        "requestId": "req-capture-1",
        "method": "POST",
        "path": "/v1/responses",
        "contentType": "application/json",
        "payload": captures[0].payload,
        "truncated": True,
        "capturedAt": capture_response.json()["capturedAt"],
    }


@pytest.mark.asyncio
async def test_deleting_api_key_cascades_verbose_captures(async_client):
    created = await async_client.post("/api/api-keys/", json={"name": "delete-capture-key"})
    key_id = created.json()["id"]
    plain_key = created.json()["key"]
    await async_client.post(
        f"/api/api-keys/{key_id}/verbose-capture",
        json={"requestCount": 2},
    )

    async with SessionLocal() as session:
        service = ApiKeysService(ApiKeysRepository(session))
        api_key = await service.validate_key(plain_key)
        assert await service.capture_verbose_request(
            api_key=api_key,
            request_id="req-delete-capture",
            method="POST",
            path="/v1/responses",
            content_type="application/json",
            body=b"{}",
        )

    disabled = await async_client.delete(f"/api/api-keys/{key_id}/verbose-capture")
    assert disabled.status_code == 200
    assert disabled.json()["verboseCaptureRemaining"] == 0
    async with SessionLocal() as session:
        capture = await session.scalar(
            select(ApiKeyVerboseCapture).where(ApiKeyVerboseCapture.api_key_id == key_id)
        )
        assert capture is not None

    deleted = await async_client.delete(f"/api/api-keys/{key_id}")
    assert deleted.status_code == 204
    async with SessionLocal() as session:
        captures = await session.scalar(
            select(ApiKeyVerboseCapture).where(ApiKeyVerboseCapture.api_key_id == key_id)
        )
        assert captures is None


@pytest.mark.asyncio
async def test_parallel_verbose_captures_cannot_overspend_budget(async_client):
    created = await async_client.post("/api/api-keys/", json={"name": "parallel-capture-key"})
    key_id = created.json()["id"]
    plain_key = created.json()["key"]
    await async_client.post(
        f"/api/api-keys/{key_id}/verbose-capture",
        json={"requestCount": 5},
    )

    async with SessionLocal() as session:
        api_key = await ApiKeysService(ApiKeysRepository(session)).validate_key(plain_key)

    async def capture(index: int) -> bool:
        async with SessionLocal() as session:
            return await ApiKeysService(ApiKeysRepository(session)).capture_verbose_request(
                api_key=api_key,
                request_id=f"req-parallel-{index}",
                method="POST",
                path="/v1/responses",
                content_type="application/json",
                body=b"{}",
            )

    results = await asyncio.gather(*(capture(index) for index in range(20)))
    assert sum(results) == 5

    async with SessionLocal() as session:
        key = await session.get(ApiKey, key_id)
        assert key is not None
        assert key.verbose_capture_remaining == 0
        capture_count = await session.scalar(
            select(func.count(ApiKeyVerboseCapture.id)).where(ApiKeyVerboseCapture.api_key_id == key_id)
        )
        assert capture_count == 5


@pytest.mark.asyncio
async def test_verbose_capture_migration_upgrade_and_downgrade(tmp_path):
    from alembic import command

    db_url = f"sqlite+aiosqlite:///{tmp_path / 'verbose-capture.sqlite'}"
    revision = "20260824_000000_add_api_key_verbose_capture"
    parent_revision = "20260718_000000_merge_refresh_claims_and_historical_facts_heads"
    merged_head = "20260901_000000_merge_production_and_verbose_capture_heads"

    await to_thread.run_sync(lambda: run_upgrade(db_url, revision, bootstrap_legacy=False))
    engine = create_async_engine(db_url, future=True)
    try:
        async with engine.connect() as connection:
            api_key_columns = {
                row[1]
                for row in (
                    await connection.exec_driver_sql("PRAGMA table_info('api_keys')")
                ).all()
            }
            capture_table = await connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'api_key_verbose_captures'"
            )
            assert "verbose_capture_remaining" in api_key_columns
            assert capture_table.scalar_one() == "api_key_verbose_captures"

        await to_thread.run_sync(
            lambda: command.downgrade(_build_alembic_config(db_url), parent_revision)
        )
        async with engine.connect() as connection:
            api_key_columns = {
                row[1]
                for row in (
                    await connection.exec_driver_sql("PRAGMA table_info('api_keys')")
                ).all()
            }
            capture_table = await connection.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'api_key_verbose_captures'"
            )
            assert "verbose_capture_remaining" not in api_key_columns
            assert capture_table.scalar_one_or_none() is None

        result = await to_thread.run_sync(
            lambda: run_upgrade(db_url, "head", bootstrap_legacy=False)
        )
        assert result.current_revision == merged_head
    finally:
        await engine.dispose()
