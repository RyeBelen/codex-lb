from __future__ import annotations

from sqlalchemy import ColumnElement, Select, and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ApiKey, ModelSource, ModelSourceModel
from app.modules.model_sources.access import source_allows_api_key


def _enablement_filter(only_disabled: bool) -> ColumnElement[bool]:
    """Enabled-state predicate for a per-capability source lookup.

    ``only_disabled`` selects the exact complement of the routable set: rows
    that match the model and the route shape but that an operator switched off,
    at the source or at the individual model. Routing needs that complement to
    tell "no source serves this model" apart from "the source that serves this
    model is switched off" -- the latter must not fall through to a
    subscription account, which rejects the model outright.
    """
    if only_disabled:
        return or_(ModelSource.is_enabled.is_(False), ModelSourceModel.is_enabled.is_(False))
    return and_(ModelSource.is_enabled.is_(True), ModelSourceModel.is_enabled.is_(True))


class ModelSourcesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def missing_api_key_ids(self, ids: list[str]) -> set[str]:
        result = await self._session.execute(select(ApiKey.id).where(ApiKey.id.in_(ids)))
        return set(ids) - set(result.scalars())

    async def _first_accessible_source(
        self, stmt: Select[tuple[ModelSource]], api_key_id: str | None
    ) -> ModelSource | None:
        # ponytail: scan matching sources; use indexed grants if candidate catalogs become large.
        result = await self._session.execute(stmt)
        return next((source for source in result.scalars() if source_allows_api_key(source, api_key_id)), None)

    async def list_sources(self) -> list[ModelSource]:
        result = await self._session.execute(
            select(ModelSource).options(selectinload(ModelSource.models)).order_by(ModelSource.name)
        )
        return list(result.scalars().unique().all())

    async def list_enabled_sources(self) -> list[ModelSource]:
        result = await self._session.execute(
            select(ModelSource)
            .options(selectinload(ModelSource.models))
            .where(ModelSource.is_enabled.is_(True))
            .order_by(ModelSource.name)
        )
        return list(result.scalars().unique().all())

    async def get_by_id(self, source_id: str) -> ModelSource | None:
        result = await self._session.execute(
            select(ModelSource).options(selectinload(ModelSource.models)).where(ModelSource.id == source_id)
        )
        return result.scalar_one_or_none()

    async def list_automatic_sources(self) -> list[ModelSource]:
        result = await self._session.execute(
            select(ModelSource)
            .where(ModelSource.is_enabled.is_(True), ModelSource.auto_discover_models.is_(True))
            .where(ModelSource.kind == "openai_compatible")
            .order_by(ModelSource.id)
        )
        return list(result.scalars().all())

    async def advance_catalog_revision(self, source: ModelSource) -> None:
        # Atomic increment also serializes operator model writes with discovery.
        await self._session.execute(
            update(ModelSource)
            .where(ModelSource.id == source.id)
            .values(catalog_revision=ModelSource.catalog_revision + 1)
        )

    async def apply_discovered_models(self, source_id: str, revision: int, models: list[ModelSourceModel]) -> bool:
        # Lock/check before reading child rows: no edit can slip between the
        # configuration check and catalog reconciliation (including on SQLite).
        result = await self._session.execute(
            update(ModelSource)
            .where(
                ModelSource.id == source_id,
                ModelSource.catalog_revision == revision,
                ModelSource.auto_discover_models.is_(True),
                ModelSource.is_enabled.is_(True),
            )
            .values(updated_at=func.now())
            .returning(ModelSource.id)
        )
        if result.scalar_one_or_none() is None:
            await self._session.rollback()
            return False
        source = await self.get_by_id(source_id)
        assert source is not None
        existing = {row.model: row for row in source.models}
        for incoming in models:
            retained = existing.pop(incoming.model, None)
            if retained is None:
                incoming.source_id = source_id
                self._session.add(incoming)
                continue
            retained.display_name = incoming.display_name
            retained.context_window = incoming.context_window
            retained.max_output_tokens = incoming.max_output_tokens
            retained.supports_streaming = incoming.supports_streaming
            retained.supports_tools = incoming.supports_tools
            retained.supports_vision = incoming.supports_vision
            retained.input_per_1m = incoming.input_per_1m
            retained.cached_input_per_1m = incoming.cached_input_per_1m
            retained.output_per_1m = incoming.output_per_1m
            retained.audio_per_minute = incoming.audio_per_minute
            retained.raw_metadata_json = incoming.raw_metadata_json
        for missing in existing.values():
            await self._session.delete(missing)
        await self._session.commit()
        return True

    async def find_chat_source_for_model(
        self,
        model: str,
        *,
        api_key_id: str | None = None,
        allowed_source_ids: set[str] | None = None,
        require_streaming: bool = False,
        only_disabled: bool = False,
    ) -> ModelSource | None:
        stmt = (
            select(ModelSource)
            .options(selectinload(ModelSource.models))
            .join(ModelSourceModel, ModelSourceModel.source_id == ModelSource.id)
            .where(ModelSource.kind == "openai_compatible")
            .where(ModelSource.supports_chat_completions.is_(True))
            .where(ModelSourceModel.model == model)
            .where(_enablement_filter(only_disabled))
            .order_by(ModelSource.name, ModelSource.id)
        )
        if require_streaming:
            stmt = stmt.where(ModelSourceModel.supports_streaming.is_(True))
        if allowed_source_ids is not None:
            if not allowed_source_ids:
                return None
            stmt = stmt.where(ModelSource.id.in_(allowed_source_ids))
        return await self._first_accessible_source(stmt, api_key_id)

    async def find_responses_source_for_model(
        self,
        model: str,
        *,
        api_key_id: str | None = None,
        allowed_source_ids: set[str] | None = None,
        require_streaming: bool = False,
        only_disabled: bool = False,
    ) -> ModelSource | None:
        stmt = (
            select(ModelSource)
            .options(selectinload(ModelSource.models))
            .join(ModelSourceModel, ModelSourceModel.source_id == ModelSource.id)
            .where(ModelSource.kind == "openai_compatible")
            .where(ModelSource.supports_responses.is_(True))
            .where(ModelSourceModel.model == model)
            .where(_enablement_filter(only_disabled))
            .order_by(ModelSource.name, ModelSource.id)
        )
        if require_streaming:
            stmt = stmt.where(ModelSourceModel.supports_streaming.is_(True))
        if allowed_source_ids is not None:
            if not allowed_source_ids:
                return None
            stmt = stmt.where(ModelSource.id.in_(allowed_source_ids))
        return await self._first_accessible_source(stmt, api_key_id)

    async def find_audio_transcriptions_source_for_model(
        self,
        model: str,
        *,
        api_key_id: str | None = None,
        allowed_source_ids: set[str] | None = None,
    ) -> ModelSource | None:
        stmt = (
            select(ModelSource)
            .options(selectinload(ModelSource.models))
            .join(ModelSourceModel, ModelSourceModel.source_id == ModelSource.id)
            .where(ModelSource.kind == "openai_compatible")
            .where(ModelSource.is_enabled.is_(True))
            .where(ModelSource.supports_audio_transcriptions.is_(True))
            .where(ModelSourceModel.model == model)
            .where(ModelSourceModel.is_enabled.is_(True))
            .order_by(ModelSource.name, ModelSource.id)
        )
        if allowed_source_ids is not None:
            if not allowed_source_ids:
                return None
            stmt = stmt.where(ModelSource.id.in_(allowed_source_ids))
        return await self._first_accessible_source(stmt, api_key_id)

    async def find_embeddings_source_for_model(
        self,
        model: str,
        *,
        api_key_id: str | None = None,
        allowed_source_ids: set[str] | None = None,
    ) -> ModelSource | None:
        stmt = (
            select(ModelSource)
            .options(selectinload(ModelSource.models))
            .join(ModelSourceModel, ModelSourceModel.source_id == ModelSource.id)
            .where(ModelSource.kind == "openai_compatible")
            .where(ModelSource.is_enabled.is_(True))
            .where(ModelSource.supports_embeddings.is_(True))
            .where(ModelSourceModel.model == model)
            .where(ModelSourceModel.is_enabled.is_(True))
            .order_by(ModelSource.name, ModelSource.id)
        )
        if allowed_source_ids is not None:
            if not allowed_source_ids:
                return None
            stmt = stmt.where(ModelSource.id.in_(allowed_source_ids))
        return await self._first_accessible_source(stmt, api_key_id)

    async def create(self, row: ModelSource, *, commit: bool = True) -> ModelSource:
        self._session.add(row)
        if commit:
            await self._session.commit()
            await self._session.refresh(row, attribute_names=["models"])
        return row

    async def delete(self, source_id: str) -> bool:
        result = await self._session.execute(
            select(ModelSource)
            .options(
                selectinload(ModelSource.models),
                selectinload(ModelSource.api_key_assignments),
            )
            .where(ModelSource.id == source_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def replace_models(
        self,
        source: ModelSource,
        models: list[ModelSourceModel],
        *,
        commit: bool = True,
    ) -> None:
        await self._session.execute(delete(ModelSourceModel).where(ModelSourceModel.source_id == source.id))
        for model in models:
            model.source_id = source.id
            self._session.add(model)
        if commit:
            await self._session.commit()
            await self._session.refresh(source, attribute_names=["models"])

    async def refresh_models(self, source: ModelSource) -> None:
        await self._session.refresh(source, attribute_names=["models"])

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
