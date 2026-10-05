"""Source-side API-key access, shared by selection and catalogs."""

from __future__ import annotations

import json

from app.db.models import ModelSource


def source_allowed_api_key_ids(source: ModelSource) -> list[str]:
    if source.allowed_api_key_ids_json is None:
        return []
    ids = json.loads(source.allowed_api_key_ids_json)
    if not isinstance(ids, list) or any(not isinstance(value, str) or not value for value in ids):
        raise ValueError("Invalid model source API-key whitelist")
    return ids


def source_allows_api_key(source: ModelSource, api_key_id: str | None) -> bool:
    ids = source_allowed_api_key_ids(source)
    return not ids or api_key_id in ids
