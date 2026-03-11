from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.db.models import StickySessionKind
from app.modules.shared.schemas import DashboardModel


class StickySessionEntryResponse(DashboardModel):
    key: str
    account_id: str
    kind: StickySessionKind
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    is_stale: bool


class StickySessionsListResponse(DashboardModel):
    entries: list[StickySessionEntryResponse] = Field(default_factory=list)


class StickySessionDeleteResponse(DashboardModel):
    status: str


class StickySessionsPurgeRequest(DashboardModel):
    stale_only: bool = True


class StickySessionsPurgeResponse(DashboardModel):
    deleted_count: int
