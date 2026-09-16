from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from app.modules.accounts.access_repository import AccountAccessRepository
from app.modules.proxy import account_access


@pytest.fixture(autouse=True)
def isolated_account_access_store(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep isolated unit tests independent of database-backed access policy.

    Tests that request db_setup use the real policy repository. Other unit tests
    model an empty grant store, preserving key scope in the proxy helper. Route,
    persistence, and revocation coverage lives in the account access integration
    suites and does not use this fixture.
    """
    if "db_setup" in request.fixturenames or "_reset_db_state" in request.fixturenames:
        return

    async def filter_scope(api_key_id: str | None, account_ids: set[str] | None) -> set[str] | None:
        return account_ids

    @asynccontextmanager
    async def session():
        yield AsyncMock()

    monkeypatch.setattr(account_access, "get_background_session", session)
    monkeypatch.setattr(AccountAccessRepository, "filter_scope", AsyncMock(side_effect=filter_scope))
    monkeypatch.setattr(AccountAccessRepository, "is_denied", AsyncMock(return_value=False))
