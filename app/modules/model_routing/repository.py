from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import and_, delete, false, or_, select
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

    async def list_account_models(self, account_id: str) -> list[str] | None:
        account_exists = await self._session.scalar(
            select(Account.id).where(Account.id == account_id, Account.delete_requested_at.is_(None))
        )
        if account_exists is None:
            return None
        return list(
            await self._session.scalars(
                select(ModelAccountGrant.model)
                .where(ModelAccountGrant.account_id == account_id)
                .order_by(ModelAccountGrant.model)
            )
        )

    async def scope(self, model: str | None, *, allow_model_less: bool = True) -> set[str] | None:
        if model is None and allow_model_less:
            return None
        if await self._session.scalar(select(ModelAccountGrant.account_id).limit(1)) is None:
            return None
        reserved = select(ModelAccountGrant.account_id).where(ModelAccountGrant.account_id == Account.id).exists()
        permitted = (
            select(ModelAccountGrant.account_id)
            .where(ModelAccountGrant.account_id == Account.id, ModelAccountGrant.model == model.strip().lower())
            .exists()
            if model is not None
            else false()
        )
        return set(
            await self._session.scalars(
                select(Account.id).where(Account.delete_requested_at.is_(None), or_(~reserved, permitted))
            )
        )

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

    async def replace_account(self, account_id: str, models: list[str]) -> None:
        try:
            async with sqlite_writer_section():
                account = await self._session.scalar(
                    select(Account)
                    .where(Account.id == account_id, Account.delete_requested_at.is_(None))
                    .with_for_update()
                )
                if account is None:
                    raise UnknownRoutingAccountError("Unknown or deleted routing account")

                selected = sorted(set(models))
                current = set(
                    await self._session.scalars(
                        select(ModelAccountGrant.model)
                        .where(ModelAccountGrant.account_id == account_id)
                        .with_for_update()
                    )
                )
                existing_policies = set(
                    await self._session.scalars(
                        select(ModelAccountPolicy.model).where(ModelAccountPolicy.model.in_(selected)).with_for_update()
                    )
                )
                await self._session.execute(delete(ModelAccountGrant).where(ModelAccountGrant.account_id == account_id))
                self._session.add_all(
                    ModelAccountPolicy(model=model) for model in selected if model not in existing_policies
                )
                await self._session.flush()
                self._session.add_all(ModelAccountGrant(model=model, account_id=account_id) for model in selected)
                await self._session.flush()

                affected = current | set(selected)
                if affected:
                    has_grants = (
                        select(ModelAccountGrant.model)
                        .where(ModelAccountGrant.model == ModelAccountPolicy.model)
                        .exists()
                    )
                    await self._session.execute(
                        delete(ModelAccountPolicy).where(ModelAccountPolicy.model.in_(affected), ~has_grants)
                    )
                await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise RoutingPolicyConflictError("Routing policy changed concurrently. Reload and try again.") from exc
        except UnknownRoutingAccountError:
            await self._session.rollback()
            raise
