"""Intersect client account scope and account grants using committed policy."""

from app.core.clients.proxy import ProxyResponseError
from app.core.errors import openai_error
from app.db.session import get_background_session
from app.modules.accounts.access_repository import AccountAccessRepository
from app.modules.api_keys.service import ApiKeyData


async def resolve_account_scope(api_key: ApiKeyData | None) -> set[str] | None:
    scoped = (
        set(api_key.assigned_account_ids) if api_key is not None and api_key.account_assignment_scope_enabled else None
    )
    async with get_background_session() as session:
        return await AccountAccessRepository(session).filter_scope(api_key.id if api_key else None, scoped)


async def require_account_access(account_id: str, api_key: ApiKeyData | None) -> None:
    outside_key_scope = (
        api_key is not None
        and api_key.account_assignment_scope_enabled
        and account_id not in api_key.assigned_account_ids
    )
    async with get_background_session() as session:
        denied = outside_key_scope or await AccountAccessRepository(session).is_denied(
            account_id, api_key.id if api_key else None
        )
    if denied:
        raise ProxyResponseError(
            403,
            openai_error(
                "account_access_denied", "This API key cannot use the requested account.", error_type="permission_error"
            ),
        )
