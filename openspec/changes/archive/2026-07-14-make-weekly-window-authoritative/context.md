## Purpose and scope

The weekly usage window is the account-wide capacity boundary. When the latest current weekly sample is exhausted, codex-lb must stop routing requests to that account even if the 5-hour window remains available or the upstream payload omits credit metadata entirely.

This change does not make every local usage value authoritative. It applies specifically to a recognized weekly/secondary standard window whose reset deadline has not elapsed. Unknown, missing, stale-after-reset, and non-weekly additional windows retain their existing handling.

## Decision rationale

The previous advisory rule avoided false local blocks when usage snapshots lagged upstream. In practice it also allowed a known weekly-zero account to be preferred by reset ordering or retained by sticky affinity, producing an upstream usage-limit failure. The weekly window now wins because it represents the broader account-wide boundary; a narrower 5-hour window cannot restore capacity that the broader window has exhausted.

Credit fields are excluded from the decision. Some plans never report them, while others can report capability-like flags alongside a zero displayed balance. Using those fields makes identical weekly windows behave differently across plan payloads.

## Constraints and failure modes

- Elapsed weekly windows must not remain hard blocks; existing reset normalization and post-reset refresh behavior remain responsible for recovery.
- Primary exhaustion still maps to `rate_limited` when weekly capacity is available.
- Sticky ownership cannot override weekly exhaustion. Safe replay and owner-bound request rules still determine whether an already-started request can move after an upstream failure.
- Independently gated additional-quota requests retain their existing documented exception and are outside this standard-window change.

## Concrete example

Given an account with 5-hour `used_percent = 1`, weekly `used_percent = 100`, weekly reset in one day, and no credit fields, the dashboard reports `quota_exceeded` and foreground selection excludes it. The same result applies when the payload reports `credits_has = true`, `credits_unlimited = true`, or a positive credit balance.

## Operational notes

After rollout, weekly-exhausted accounts should disappear from selection logs until their derived window resets. Upstream `usage_limit_reached` errors should decline; any remaining cases indicate missing or stale weekly telemetry rather than a credit-override path.
