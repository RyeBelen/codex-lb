## Why

The production dashboard counts accounts with exhausted weekly quota as active because credit metadata overrides the authoritative long-window usage state. This also leaves those accounts selectable even though upstream has no weekly capacity for them.

## What Changes

- Treat an exhausted weekly usage window as `quota_exceeded`, regardless of `credits_has`, `credits_unlimited`, or `credits_balance` metadata.
- Apply the same effective status to proxy selection and account/dashboard summaries.
- Preserve explicit paused, deactivated, and reauthentication states.
- Add regression coverage for account summaries, dashboard overview, routing, persistence, and sticky-session fallback.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `usage-refresh-policy`: Make the authoritative long-window percentage take precedence over credit metadata when deriving account availability.

## Impact

This changes quota status derivation in `app/core/usage/quota.py` and proxy state construction, updates affected tests, and changes the dashboard active/unavailable counts. No schema, migration, API shape, or upstream contribution is involved.
