from app.core.clients.proxy import ProxyResponseError
from app.core.errors import openai_error
from app.db.session import get_background_session
from app.modules.model_routing.repository import ModelRoutingRepository


def check_model_account_scope(account_id: str, scope: set[str] | None) -> None:
    if scope is not None and account_id not in scope:
        raise ProxyResponseError(
            403,
            openai_error(
                "model_account_not_allowed",
                "This account is not permitted to serve the requested model.",
                error_type="permission_error",
            ),
        )


async def require_model_account_access(account_id: str, model: str) -> None:
    async with get_background_session() as session:
        scope = await ModelRoutingRepository(session).scope(model)
    check_model_account_scope(account_id, scope)
