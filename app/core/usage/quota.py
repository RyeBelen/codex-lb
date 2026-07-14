from __future__ import annotations

import time

from app.core import usage as usage_core
from app.db.models import AccountStatus


def apply_usage_quota(
    *,
    status: AccountStatus,
    primary_used: float | None,
    primary_reset: int | None,
    primary_window_minutes: int | None,
    runtime_reset: float | None,
    secondary_used: float | None,
    secondary_reset: int | None,
    credits_has: bool | None = None,
    credits_unlimited: bool | None = None,
    credits_balance: float | None = None,
    infer_status_from_usage: bool = True,
    infer_primary_status_from_usage: bool | None = None,
    infer_secondary_status_from_usage: bool | None = None,
) -> tuple[AccountStatus, float | None, float | None]:
    used_percent = primary_used
    reset_at = runtime_reset
    infer_primary_status = (
        infer_status_from_usage if infer_primary_status_from_usage is None else infer_primary_status_from_usage
    )
    infer_secondary_status = (
        infer_status_from_usage if infer_secondary_status_from_usage is None else infer_secondary_status_from_usage
    )

    if status in (AccountStatus.REAUTH_REQUIRED, AccountStatus.DEACTIVATED, AccountStatus.PAUSED):
        return status, used_percent, reset_at

    if secondary_used is not None:
        if secondary_used >= 100.0:
            used_percent = 100.0
            if infer_secondary_status:
                if secondary_reset is not None:
                    reset_at = secondary_reset
                status = AccountStatus.QUOTA_EXCEEDED
                return status, used_percent, reset_at
        if status == AccountStatus.QUOTA_EXCEEDED:
            if runtime_reset and runtime_reset > time.time():
                reset_at = runtime_reset
            else:
                status = AccountStatus.ACTIVE
                reset_at = None
    elif status == AccountStatus.QUOTA_EXCEEDED and secondary_reset is not None and infer_secondary_status:
        reset_at = secondary_reset

    if primary_used is not None:
        if primary_used >= 100.0:
            used_percent = 100.0
            if infer_primary_status:
                if primary_reset is not None:
                    reset_at = primary_reset
                else:
                    reset_at = _fallback_primary_reset(primary_window_minutes) or reset_at
                status = AccountStatus.RATE_LIMITED
                return status, used_percent, reset_at
        if status == AccountStatus.RATE_LIMITED:
            if runtime_reset and runtime_reset > time.time():
                reset_at = runtime_reset
            else:
                status = AccountStatus.ACTIVE
                reset_at = None
    elif status == AccountStatus.RATE_LIMITED and secondary_used is not None and secondary_used < 100.0:
        # No primary data at all — upstream stopped reporting the short
        # window. The long-window sample proves availability, so the block
        # clears once its runtime reset elapses instead of pinning the
        # account rate-limited indefinitely. Callers that cannot tie the
        # sample to a reset deadline or post-block evidence must preserve
        # the block themselves.
        if runtime_reset and runtime_reset > time.time():
            reset_at = runtime_reset
        else:
            status = AccountStatus.ACTIVE
            reset_at = None

    return status, used_percent, reset_at


def _fallback_primary_reset(primary_window_minutes: int | None) -> float | None:
    window_minutes = primary_window_minutes or usage_core.default_window_minutes("primary")
    if not window_minutes:
        return None
    return time.time() + float(window_minutes) * 60.0
