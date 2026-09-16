from app.modules.model_routing.repository import ModelRoutingRepository
from app.modules.model_routing.schemas import ModelRoutingPolicies, ModelRoutingPolicy


class ModelRoutingService:
    def __init__(self, repository: ModelRoutingRepository) -> None:
        self._repository = repository

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
