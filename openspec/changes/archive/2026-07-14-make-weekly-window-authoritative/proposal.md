## Why

Accounts whose current weekly usage window is exhausted can remain marked active and be selected because local usage is advisory and credit metadata can override the exhausted window. This causes avoidable upstream usage-limit failures even though the dashboard already has a current `100%` weekly sample.

## What Changes

- **BREAKING** Make a current, unexpired weekly/secondary window at `used_percent >= 100` an account-wide `quota_exceeded` signal for status derivation and foreground routing.
- Stop using `credits_has`, `credits_unlimited`, or `credits_balance` to override an exhausted weekly window.
- Ensure an available 5-hour/primary window, sticky affinity, and reset ordering do not make a weekly-exhausted account selectable for standard routing.
- Preserve primary-window `rate_limited` precedence when the weekly window is not exhausted and preserve elapsed-window recovery.
- Add regression coverage for dashboard status, proxy selection, reset-drain ordering, sticky routing, and credit metadata variants.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `account-routing`: Make a current exhausted weekly window authoritative for foreground account eligibility instead of advisory.
- `usage-refresh-policy`: Remove credit-backed overrides for current weekly-window exhaustion while preserving reset recovery.

## Impact

- Affected code: shared usage quota derivation, proxy account-state construction, sticky selection, and account/dashboard summaries.
- Affected behavior: accounts at weekly `used_percent >= 100` will no longer receive standard foreground requests until the window resets or a newer current window reports availability. Existing independently gated additional-quota requests retain their documented exception.
- No API schema, database schema, migration, or dependency changes are required.
