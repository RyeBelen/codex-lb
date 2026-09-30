## Why
Expiring reset credits can restore exhausted weekly quota before the existing five-minute fallback becomes eligible.

## What Changes
- Add an default-off per-account weekly-exhaustion opt-in with a fixed seven-day credit-expiry window and at least 24h until natural weekly refresh.
- Confirm fresh weekly exhaustion under existing redemption serialization before consuming.
- Retain automatic pins for eight days while preserving manual 24-hour retention.

## Capabilities
### New Capabilities
None.
### Modified Capabilities
- `rate-limit-reset-credits`: early weekly reset and extended automatic pin retention.
- `frontend-architecture`: per-account weekly-empty switch.
- `database-migrations`: persisted default-off Account Boolean.

## Impact
Existing scheduler, shared redemption helper, settings contract/UI, migration, and focused regression tests. No new dependencies or scheduler.
