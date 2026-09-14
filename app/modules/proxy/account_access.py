"""Intersect client account scope and account grants using committed policy."""

from app.core.clients.proxy import ProxyResponseError
from app.core.errors import openai_error
from app.db.session import get_background_session
from app.modules.accounts.access_repository import AccountAccessRepository
from app.modules.api_keys.service import ApiKeyData
from app.modules.model_routing.access import check_model_account_scope
from app.modules.model_routing.repository import ModelRoutingRepository


async def resolve_account_scope(
    api_key: ApiKeyData | None, *, model: str | None = None, allow_model_less: bool = True
) -> set[str] | None:
    scoped = (
        set(api_key.assigned_account_ids) if api_key is not None and api_key.account_assignment_scope_enabled else None
    )
    async with get_background_session() as session:
        scoped = await AccountAccessRepository(session).filter_scope(api_key.id if api_key else None, scoped)
        model_scope = await ModelRoutingRepository(session).scope(model, allow_model_less=allow_model_less)
        if model_scope is not None:
            return model_scope if scoped is None else scoped & model_scope
        return scoped


async def require_account_access(
    account_id: str, api_key: ApiKeyData | None, *, model: str | None = None, allow_model_less: bool = True
) -> None:
    outside_key_scope = (
        api_key is not None
        and api_key.account_assignment_scope_enabled
        and account_id not in api_key.assigned_account_ids
    )
    async with get_background_session() as session:
        denied = outside_key_scope or await AccountAccessRepository(session).is_denied(
            account_id, api_key.id if api_key else None
        )
        model_scope = await ModelRoutingRepository(session).scope(model, allow_model_less=allow_model_less)
    check_model_account_scope(account_id, model_scope)
    if denied:
        raise ProxyResponseError(
            403,
            openai_error(
                "account_access_denied", "This API key cannot use the requested account.", error_type="permission_error"
            ),
        )
