from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, ModelAccountGrant, ModelAccountPolicy
from app.db.session import sqlite_writer_section


@dataclass(frozen=True, slots=True)
class ModelAccountRule:
    model: str
    account_ids: list[str]


class UnknownRoutingAccountError(ValueError):
    pass


class RoutingPolicyConflictError(ValueError):
    pass


class ModelRoutingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_rules(self, model: str | None = None) -> list[ModelAccountRule]:
        query = (
            select(ModelAccountPolicy.model, Account.id)
            .outerjoin(ModelAccountGrant, ModelAccountGrant.model == ModelAccountPolicy.model)
            .outerjoin(
                Account,
                and_(Account.id == ModelAccountGrant.account_id, Account.delete_requested_at.is_(None)),
            )
            .order_by(ModelAccountPolicy.model, Account.id)
        )
        if model is not None:
            query = query.where(ModelAccountPolicy.model == model.strip().lower())
        rules: dict[str, list[str]] = {}
        for model_id, account_id in (await self._session.execute(query)).all():
            accounts = rules.setdefault(model_id, [])
            if account_id is not None:
                accounts.append(account_id)
        return [ModelAccountRule(model_id, account_ids) for model_id, account_ids in rules.items()]

    async def scope(self, model: str | None) -> set[str] | None:
        if model is None:
            return None
        rules = await self.list_rules(model)
        return set(rules[0].account_ids) if rules else None

    async def replace(self, model: str, account_ids: list[str] | None) -> None:
        try:
            async with sqlite_writer_section():
                policy = await self._session.scalar(
                    select(ModelAccountPolicy).where(ModelAccountPolicy.model == model).with_for_update()
                )
                if account_ids is None:
                    if policy is not None:
                        await self._session.execute(delete(ModelAccountGrant).where(ModelAccountGrant.model == model))
                        await self._session.delete(policy)
                else:
                    ids = sorted(set(account_ids))
                    existing = set(
                        await self._session.scalars(
                            select(Account.id)
                            .where(Account.id.in_(ids), Account.delete_requested_at.is_(None))
                            .order_by(Account.id)
                            .with_for_update()
                        )
                    )
                    if existing != set(ids):
                        raise UnknownRoutingAccountError("Unknown or deleted routing account")
                    if policy is None:
                        self._session.add(ModelAccountPolicy(model=model))
                        await self._session.flush()
                    await self._session.execute(delete(ModelAccountGrant).where(ModelAccountGrant.model == model))
                    self._session.add_all(ModelAccountGrant(model=model, account_id=account_id) for account_id in ids)
                await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise RoutingPolicyConflictError("Routing policy changed concurrently. Reload and try again.") from exc
        except UnknownRoutingAccountError:
            await self._session.rollback()
            raise
