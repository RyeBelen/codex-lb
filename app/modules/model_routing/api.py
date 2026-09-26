from fastapi import APIRouter, Depends

from app.core.auth.dependencies import (
    require_dashboard_write_access,
    set_dashboard_error_format,
    validate_dashboard_session,
)
from app.core.exceptions import DashboardBadRequestError, DashboardConflictError, DashboardNotFoundError
from app.dependencies import ModelRoutingContext, get_model_routing_context
from app.modules.model_routing.repository import RoutingPolicyConflictError, UnknownRoutingAccountError
from app.modules.model_routing.schemas import (
    AccountAllowedModels,
    AccountAllowedModelsUpdate,
    ModelRoutingPolicies,
    ModelRoutingPolicy,
)
from app.modules.model_routing.service import UnsupportedAccountModelError

router = APIRouter(
    prefix="/api/model-account-routing",
    tags=["dashboard"],
    dependencies=[Depends(validate_dashboard_session), Depends(set_dashboard_error_format)],
)

account_router = APIRouter(
    prefix="/api/accounts",
    tags=["dashboard"],
    dependencies=[Depends(validate_dashboard_session), Depends(set_dashboard_error_format)],
)


@router.get("", response_model=ModelRoutingPolicies)
async def list_policies(context: ModelRoutingContext = Depends(get_model_routing_context)) -> ModelRoutingPolicies:
    return await context.service.list_policies()


@router.put("", response_model=ModelRoutingPolicy)
async def replace_policy(
    payload: ModelRoutingPolicy,
    context: ModelRoutingContext = Depends(get_model_routing_context),
    _write_access=Depends(require_dashboard_write_access),
) -> ModelRoutingPolicy:
    try:
        return await context.service.replace(payload)
    except UnknownRoutingAccountError as exc:
        raise DashboardBadRequestError(str(exc), code="invalid_routing_account") from exc
    except RoutingPolicyConflictError as exc:
        raise DashboardConflictError(str(exc), code="routing_policy_conflict") from exc


@account_router.get("/{account_id}/allowed-models", response_model=AccountAllowedModels)
async def get_account_allowed_models(
    account_id: str,
    context: ModelRoutingContext = Depends(get_model_routing_context),
) -> AccountAllowedModels:
    policy = await context.service.get_account_allowed_models(account_id)
    if policy is None:
        raise DashboardNotFoundError("Account not found", code="account_not_found")
    return policy


@account_router.put("/{account_id}/allowed-models", response_model=AccountAllowedModels)
async def replace_account_allowed_models(
    account_id: str,
    payload: AccountAllowedModelsUpdate,
    context: ModelRoutingContext = Depends(get_model_routing_context),
    _write_access=Depends(require_dashboard_write_access),
) -> AccountAllowedModels:
    try:
        return await context.service.replace_account_allowed_models(account_id, payload.allowed_models)
    except UnknownRoutingAccountError as exc:
        raise DashboardNotFoundError("Account not found", code="account_not_found") from exc
    except UnsupportedAccountModelError as exc:
        raise DashboardBadRequestError(str(exc), code="invalid_account_models") from exc
    except RoutingPolicyConflictError as exc:
        raise DashboardConflictError(str(exc), code="routing_policy_conflict") from exc
