from __future__ import annotations

import json
import logging
from typing import Annotated

import aiohttp
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from app.core.clients.http import lease_http_session
from app.db.models import ModelSource
from app.db.session import detach_session_objects, get_background_session
from app.modules.model_sources.forwarding import _source_headers, _source_timeout_seconds, _source_url
from app.modules.model_sources.repository import ModelSourcesRepository
from app.modules.model_sources.schemas import ModelSourceModelInput
from app.modules.model_sources.service import _model_inputs_to_rows

logger = logging.getLogger(__name__)

_MAX_CATALOG_BYTES = 4 * 1024 * 1024
_MAX_CATALOG_MODELS = 10_000
_MAX_FETCH_SECONDS = 30

type _PositiveInt = Annotated[int, Field(ge=1, le=2_147_483_647)]
type _Price = Annotated[float, Field(ge=0, allow_inf_nan=False)]
type _Label = Annotated[str, Field(min_length=1, max_length=255)]


class _ProviderPricing(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")

    input_per_1m: _Price | None = None
    cached_input_per_1m: _Price | None = None
    output_per_1m: _Price | None = None
    audio_per_minute: _Price | None = None


class _ReasoningLevel(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")

    effort: _Label
    description: str = Field(default="", max_length=4096)


class _ProviderMetadata(_ProviderPricing):
    display_name: _Label | None = Field(default=None, validation_alias=AliasChoices("display_name", "name"))
    description: str | None = Field(default=None, max_length=16_384)
    context_window: _PositiveInt | None = Field(
        default=None, validation_alias=AliasChoices("context_window", "context_length", "max_context_window")
    )
    max_output_tokens: _PositiveInt | None = None
    supports_streaming: bool | None = None
    supports_tools: bool | None = Field(
        default=None, validation_alias=AliasChoices("supports_tools", "supports_parallel_tool_calls")
    )
    supports_vision: bool | None = Field(
        default=None, validation_alias=AliasChoices("supports_vision", "supports_images")
    )
    input_modalities: list[_Label] | None = Field(default=None, max_length=32)
    supports_reasoning: bool | None = None
    supported_reasoning_levels: list[_Label | _ReasoningLevel] | None = Field(default=None, max_length=32)
    default_reasoning_level: _Label | None = None
    supports_reasoning_summaries: bool | None = None
    supports_search_tool: bool | None = None
    experimental_supported_tools: list[_Label] | None = Field(default=None, max_length=64)
    pricing: _ProviderPricing | None = None


class _ProviderModel(_ProviderMetadata):
    id: _Label
    object: str | None = Field(default=None, max_length=255)
    created: int | None = None
    owned_by: str | None = Field(default=None, max_length=255)
    metadata: _ProviderMetadata | None = None
    capabilities: _ProviderMetadata | None = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("Invalid model ID")
        return value


class _ProviderCatalog(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore")

    data: list[_ProviderModel] = Field(max_length=_MAX_CATALOG_MODELS)


def parse_source_catalog(body: bytes) -> list[ModelSourceModelInput]:
    if len(body) > _MAX_CATALOG_BYTES:
        raise ValueError("Model catalog exceeds size limit")
    catalog = _ProviderCatalog.model_validate_json(body)
    models: dict[str, ModelSourceModelInput] = {}
    for entry in catalog.data:
        # Only typed, supported metadata survives. Unknown keys (including
        # source IDs, credentials and operator request overrides) are dropped.
        metadata = {}
        for nested in (entry.capabilities, entry.metadata):
            if nested is not None:
                metadata.update(nested.model_dump(mode="json", exclude_none=True, exclude_unset=True))
        metadata.update(
            entry.model_dump(mode="json", exclude_none=True, exclude_unset=True, exclude={"metadata", "capabilities"})
        )
        advertised = _ProviderMetadata.model_validate(metadata)
        prices = advertised.pricing or _ProviderPricing()
        supports_reasoning = advertised.supports_reasoning
        if supports_reasoning is None:
            supports_reasoning = bool(advertised.supported_reasoning_levels)
        metadata["supports_reasoning"] = supports_reasoning
        # First advertised occurrence wins, but every entry is validated even
        # when IDs duplicate so malformed suffixes cannot partially apply.
        models.setdefault(
            entry.id,
            ModelSourceModelInput(
                model=entry.id,
                display_name=advertised.display_name,
                context_window=advertised.context_window,
                max_output_tokens=advertised.max_output_tokens,
                supports_streaming=advertised.supports_streaming if advertised.supports_streaming is not None else True,
                supports_tools=advertised.supports_tools or False,
                supports_vision=(
                    advertised.supports_vision
                    if advertised.supports_vision is not None
                    else "image" in (advertised.input_modalities or [])
                ),
                input_per_1m=advertised.input_per_1m if advertised.input_per_1m is not None else prices.input_per_1m,
                cached_input_per_1m=(
                    advertised.cached_input_per_1m
                    if advertised.cached_input_per_1m is not None
                    else prices.cached_input_per_1m
                ),
                output_per_1m=advertised.output_per_1m
                if advertised.output_per_1m is not None
                else prices.output_per_1m,
                audio_per_minute=advertised.audio_per_minute
                if advertised.audio_per_minute is not None
                else prices.audio_per_minute,
                raw_metadata_json=json.dumps(metadata, ensure_ascii=False, separators=(",", ":"), sort_keys=True),
            ),
        )
    return [models[slug] for slug in sorted(models)]


async def fetch_source_catalog(source: ModelSource) -> list[ModelSourceModelInput]:
    headers = _source_headers(source, encryptor=None, content_type=None)
    timeout = aiohttp.ClientTimeout(total=min(_source_timeout_seconds(source), _MAX_FETCH_SECONDS))
    async with lease_http_session() as session:
        async with session.get(_source_url(source, "/models"), headers=headers, timeout=timeout) as response:
            if response.status != 200:
                # Do not retain/log provider bodies, URLs or credentials.
                raise ValueError(f"Model catalog returned HTTP {response.status}")
            body = bytearray()
            async for chunk in response.content.iter_chunked(64 * 1024):
                body.extend(chunk)
                if len(body) > _MAX_CATALOG_BYTES:
                    raise ValueError("Model catalog exceeds size limit")
    return parse_source_catalog(bytes(body))


async def refresh_source_catalogs() -> None:
    try:
        async with get_background_session() as session:
            sources = await ModelSourcesRepository(session).list_automatic_sources()
            detach_session_objects(session)
    except Exception:
        logger.warning("Could not read automatic source catalogs")
        return
    # ponytail: sequential bounded fetches; bounded concurrency if source count makes a pass too slow.
    for source in sources:
        try:
            models = await fetch_source_catalog(source)
            async with get_background_session() as session:
                await ModelSourcesRepository(session).apply_discovered_models(
                    source.id, source.catalog_revision, _model_inputs_to_rows(models)
                )
        except Exception as exc:
            # Exception text may contain provider bodies or authorization data.
            logger.warning("Source catalog refresh failed source=%s error_type=%s", source.id, type(exc).__name__)
