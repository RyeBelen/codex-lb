from app.core.openai.model_registry import MODEL_SOURCE_KIND_SUBSCRIPTION, ModelRegistry, is_public_model
from app.modules.model_routing.repository import ModelRoutingRepository, UnknownRoutingAccountError
from app.modules.model_routing.schemas import (
    AccountAllowedModels,
    AccountModelOption,
    ModelRoutingPolicies,
    ModelRoutingPolicy,
)


class UnsupportedAccountModelError(ValueError):
    pass


class ModelRoutingService:
    def __init__(self, repository: ModelRoutingRepository, registry: ModelRegistry) -> None:
        self._repository = repository
        self._registry = registry

    async def list_policies(self) -> ModelRoutingPolicies:
        return ModelRoutingPolicies(
            rules=[
                ModelRoutingPolicy(model=rule.model, restricted=True, account_ids=rule.account_ids)
                for rule in await self._repository.list_rules()
            ]
        )

    async def replace(self, policy: ModelRoutingPolicy) -> ModelRoutingPolicy:
        await self._repository.replace(policy.model, policy.account_ids if policy.restricted else None)
        return policy

    async def get_account_allowed_models(self, account_id: str) -> AccountAllowedModels | None:
        allowed_models = await self._repository.list_account_models(account_id)
        if allowed_models is None:
            return None
        available_models, catalog_available = self._resolved_account_models(account_id)
        return AccountAllowedModels(
            account_id=account_id,
            allowed_models=allowed_models,
            available_models=available_models,
            catalog_available=catalog_available,
        )

    async def replace_account_allowed_models(self, account_id: str, allowed_models: list[str]) -> AccountAllowedModels:
        current = await self.get_account_allowed_models(account_id)
        if current is None:
            raise UnknownRoutingAccountError("Unknown or deleted routing account")
        accepted = {model.id for model in current.available_models} | set(current.allowed_models)
        unsupported = sorted(set(allowed_models) - accepted)
        if unsupported:
            raise UnsupportedAccountModelError(f"Models are not available to this account: {', '.join(unsupported)}")
        await self._repository.replace_account(account_id, allowed_models)
        updated = await self.get_account_allowed_models(account_id)
        if updated is None:
            raise UnknownRoutingAccountError("Unknown or deleted routing account")
        return updated

    def _resolved_account_models(self, account_id: str) -> tuple[list[AccountModelOption], bool]:
        snapshot = self._registry.get_snapshot()
        models = self._registry.get_models_with_fallback()
        if snapshot is None or account_id not in snapshot.account_plans:
            slugs = models.keys()
            catalog_available = False
        else:
            slugs = (slug for slug, account_ids in snapshot.model_accounts.items() if account_id in account_ids)
            catalog_available = True
        options = {
            slug: AccountModelOption(id=slug, name=model.display_name or slug)
            for slug in slugs
            if (model := models.get(slug)) is not None
            and model.source_kind == MODEL_SOURCE_KIND_SUBSCRIPTION
            and is_public_model(model, None)
        }
        return [options[slug] for slug in sorted(options)], catalog_available
