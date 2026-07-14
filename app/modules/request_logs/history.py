from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select, union_all
from sqlalchemy.sql import Select
from sqlalchemy.sql.selectable import Subquery

from app.db.models import RequestLog, RequestLogHistoricalFact

HISTORY_COLUMNS = (
    "account_id",
    "api_key_id",
    "session_id",
    "request_id",
    "requested_at",
    "deleted_at",
    "model",
    "reasoning_effort",
    "service_tier",
    "source",
    "useragent_group",
    "request_kind",
    "status",
    "error_code",
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "reasoning_tokens",
    "cost_usd",
    "latency_ms",
    "latency_first_token_ms",
)

FACT_INSERT_COLUMNS = ("request_log_id", *HISTORY_COLUMNS)


def historical_fact_projection(ids: Sequence[int]) -> Select:
    return select(
        RequestLog.id.label("request_log_id"),
        *(getattr(RequestLog, column).label(column) for column in HISTORY_COLUMNS),
    ).where(RequestLog.id.in_(ids))


def request_history_selectable(*, name: str = "request_history") -> Subquery:
    facts = select(
        RequestLogHistoricalFact.request_log_id.label("id"),
        *(getattr(RequestLogHistoricalFact, column).label(column) for column in HISTORY_COLUMNS),
    )
    raw = select(
        RequestLog.id.label("id"),
        *(getattr(RequestLog, column).label(column) for column in HISTORY_COLUMNS),
    )
    return union_all(facts, raw).subquery(name)
