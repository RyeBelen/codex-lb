## Context
Reuse the existing scheduler and serialized redeem helper. The old five-minute global setting remains independent. No new global setting is added. Existing account/expiry-date automatic request identity remains conservative across both modes.

## Decisions
The new rule requires finite raw weekly used percentage >=100 and 0 < credit expiry delta <=604800 seconds. Five-hour and monthly quotas do not qualify. A persisted weekly sample only filters candidates; refresh usage inside the redeem lock and require fresh weekly evidence before pinning. Missing/failed evidence or a weekly deadline less than 24h away skips. Recheck the account opt-in inside the lock and the 24h floor again just before pinning after credit fetch. Retain auto namespace pins eight days on both reads and purges; manual retention remains 24h.

## Risks
Same-expiry-date coupons are intentionally suppressed by the existing automatic request identity. Natural weekly recovery may be close; there is no extra time-to-reset threshold. Polling interval and work duration determine latency.

## Verification
Mock all upstream interactions. Test boundaries, legacy behavior, usage refresh failures and missing weekly data, race/target checks, TTL reads/purges, settings API/audit/UI, and migration upgrade/downgrade.

## Account contract
Extend the existing account PATCH, account_updated audit, summary and update mutation. Update supported account preferences atomically. New/existing accounts default off; reimports preserve existing preferences. Busy/read-only users cannot mutate the switch. Newly enabling is rejected when reset-credit polling is disabled; unchanged preferences remain savable.
