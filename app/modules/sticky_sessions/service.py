from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.utils.time import to_utc_naive, utcnow
from app.db.models import StickySession, StickySessionKind
from app.modules.proxy.sticky_repository import StickySessionsRepository
from app.modules.settings.repository import SettingsRepository


@dataclass(frozen=True, slots=True)
class StickySessionEntryData:
    key: str
    account_id: str
    kind: StickySessionKind
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None
    is_stale: bool


class StickySessionsService:
    def __init__(
        self,
        repository: StickySessionsRepository,
        settings_repository: SettingsRepository,
    ) -> None:
        self._repository = repository
        self._settings_repository = settings_repository

    async def list_entries(
        self,
        *,
        kind: StickySessionKind | None = None,
        stale_only: bool = False,
        limit: int = 100,
    ) -> list[StickySessionEntryData]:
        settings = await self._settings_repository.get_or_create()
        ttl_seconds = settings.openai_cache_affinity_max_age_seconds
        rows = await self._repository.list_entries(kind=kind, limit=limit)
        entries = [self._to_entry(row, ttl_seconds=ttl_seconds) for row in rows]
        if stale_only:
            return [entry for entry in entries if entry.is_stale]
        return entries

    async def delete_entry(self, key: str) -> bool:
        return await self._repository.delete(key)

    async def purge_entries(self, *, stale_only: bool) -> int:
        if not stale_only:
            return await self._repository.purge_all()
        settings = await self._settings_repository.get_or_create()
        cutoff = utcnow() - timedelta(seconds=settings.openai_cache_affinity_max_age_seconds)
        return await self._repository.purge_prompt_cache_before(cutoff)

    def _to_entry(self, row: StickySession, *, ttl_seconds: int) -> StickySessionEntryData:
        expires_at: datetime | None = None
        is_stale = False
        if row.kind == StickySessionKind.PROMPT_CACHE:
            expires_at = to_utc_naive(row.updated_at) + timedelta(seconds=ttl_seconds)
            is_stale = expires_at <= utcnow()
        return StickySessionEntryData(
            key=row.key,
            account_id=row.account_id,
            kind=row.kind,
            created_at=row.created_at,
            updated_at=row.updated_at,
            expires_at=expires_at,
            is_stale=is_stale,
        )
