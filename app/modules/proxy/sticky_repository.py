from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Insert, func

from app.core.utils.time import to_utc_naive, utcnow
from app.db.models import StickySession, StickySessionKind


class StickySessionsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_account_id(
        self,
        key: str,
        *,
        kind: StickySessionKind,
        max_age_seconds: int | None = None,
    ) -> str | None:
        if not key:
            return None
        row = await self.get_entry(key, kind=kind)
        if row is None:
            return None
        if max_age_seconds is not None:
            cutoff = utcnow() - timedelta(seconds=max_age_seconds)
            if to_utc_naive(row.updated_at) < cutoff:
                await self.delete(key, kind=kind)
                return None
        return row.account_id

    async def get_entry(self, key: str, *, kind: StickySessionKind | None = None) -> StickySession | None:
        if not key:
            return None
        statement = select(StickySession).where(StickySession.key == key)
        if kind is not None:
            statement = statement.where(StickySession.kind == kind)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert(self, key: str, account_id: str, *, kind: StickySessionKind) -> StickySession:
        statement = self._build_upsert_statement(key, account_id, kind)
        await self._session.execute(statement)
        await self._session.commit()
        row = await self.get_entry(key)
        if row is None:
            raise RuntimeError(f"StickySession upsert failed for key={key!r}")
        await self._session.refresh(row)
        return row

    async def delete(self, key: str, *, kind: StickySessionKind | None = None) -> bool:
        if not key:
            return False
        statement = delete(StickySession).where(StickySession.key == key)
        if kind is not None:
            statement = statement.where(StickySession.kind == kind)
        result = await self._session.execute(statement.returning(StickySession.key))
        await self._session.commit()
        return result.scalar_one_or_none() is not None

    async def list_entries(
        self,
        *,
        kind: StickySessionKind | None = None,
        limit: int | None = None,
    ) -> Sequence[StickySession]:
        statement = select(StickySession).order_by(
            StickySession.updated_at.desc(),
            StickySession.created_at.desc(),
            StickySession.key.asc(),
        )
        if kind is not None:
            statement = statement.where(StickySession.kind == kind)
        if limit is not None:
            statement = statement.limit(limit)
        result = await self._session.execute(statement)
        return result.scalars().all()

    async def purge_prompt_cache_before(self, cutoff: datetime) -> int:
        result = await self._session.execute(
            delete(StickySession)
            .where(StickySession.kind == StickySessionKind.PROMPT_CACHE)
            .where(StickySession.updated_at < to_utc_naive(cutoff))
            .returning(StickySession.key)
        )
        deleted = len(result.scalars().all())
        await self._session.commit()
        return deleted

    async def purge_all(self) -> int:
        result = await self._session.execute(delete(StickySession).returning(StickySession.key))
        deleted = len(result.scalars().all())
        await self._session.commit()
        return deleted

    def _build_upsert_statement(self, key: str, account_id: str, kind: StickySessionKind) -> Insert:
        dialect = self._session.get_bind().dialect.name
        if dialect == "postgresql":
            insert_fn = pg_insert
        elif dialect == "sqlite":
            insert_fn = sqlite_insert
        else:
            raise RuntimeError(f"StickySession upsert unsupported for dialect={dialect!r}")
        statement = insert_fn(StickySession).values(key=key, account_id=account_id, kind=kind)
        return statement.on_conflict_do_update(
            index_elements=[StickySession.key],
            set_={
                "account_id": account_id,
                "kind": kind,
                "updated_at": func.now(),
            },
        )
