from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, AccountApiKeyGrant, ApiKey
from app.db.session import sqlite_writer_section


@dataclass(frozen=True, slots=True)
class AccountAccessPolicy:
    restricted: bool
    api_key_ids: list[str]


class UnknownAccessKeyError(ValueError):
    pass


class AccountAccessRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, account_id: str) -> AccountAccessPolicy | None:
        rows = (
            await self._session.execute(
                select(Account.api_key_access_restricted, AccountApiKeyGrant.api_key_id)
                .outerjoin(AccountApiKeyGrant, AccountApiKeyGrant.account_id == Account.id)
                .where(Account.id == account_id, Account.delete_requested_at.is_(None))
                .order_by(AccountApiKeyGrant.api_key_id)
            )
        ).all()
        if not rows:
            return None
        return AccountAccessPolicy(
            restricted=rows[0][0], api_key_ids=[key_id for _, key_id in rows if key_id is not None]
        )

    async def replace(self, account_id: str, policy: AccountAccessPolicy) -> bool:
        async with sqlite_writer_section():
            # Lock the account before replacing its grants, also serializing PostgreSQL writers.
            account_id_found = await self._session.scalar(
                select(Account.id)
                .where(Account.id == account_id, Account.delete_requested_at.is_(None))
                .with_for_update()
            )
            if account_id_found is None:
                return False
            key_ids = sorted(set(policy.api_key_ids))
            existing = set(
                await self._session.scalars(
                    select(ApiKey.id).where(ApiKey.id.in_(key_ids)).order_by(ApiKey.id).with_for_update()
                )
            )
            if existing != set(key_ids):
                raise UnknownAccessKeyError("Unknown API key IDs: " + ", ".join(sorted(set(key_ids) - existing)))
            await self._session.execute(
                update(Account).where(Account.id == account_id).values(api_key_access_restricted=policy.restricted)
            )
            await self._session.execute(delete(AccountApiKeyGrant).where(AccountApiKeyGrant.account_id == account_id))
            self._session.add_all(
                AccountApiKeyGrant(account_id=account_id, api_key_id=key_id) for key_id in key_ids if policy.restricted
            )
            await self._session.commit()
            return True

    async def denied_account_ids(self, api_key_id: str | None) -> set[str]:
        granted = select(AccountApiKeyGrant.account_id).where(AccountApiKeyGrant.api_key_id == api_key_id)
        rows = await self._session.scalars(
            select(Account.id).where(Account.api_key_access_restricted.is_(True), Account.id.not_in(granted))
        )
        return set(rows)

    async def is_denied(self, account_id: str, api_key_id: str | None) -> bool:
        granted = select(AccountApiKeyGrant.account_id).where(AccountApiKeyGrant.api_key_id == api_key_id)
        return (
            await self._session.scalar(
                select(Account.id).where(
                    Account.id == account_id, Account.api_key_access_restricted.is_(True), Account.id.not_in(granted)
                )
            )
            is not None
        )

    async def filter_scope(self, api_key_id: str | None, account_ids: set[str] | None) -> set[str] | None:
        denied = await self.denied_account_ids(api_key_id)
        if not denied:
            return account_ids
        if account_ids is not None:
            return account_ids - denied
        return set(await self._session.scalars(select(Account.id).where(Account.id.not_in(denied))))
