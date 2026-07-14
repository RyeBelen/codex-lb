## Context

The shared `apply_usage_quota` helper currently has two behaviors that conflict with the requested account-wide weekly boundary: credit metadata can clear secondary exhaustion, and proxy state construction disables usage-based status inference. Selection strategies and sticky affinity then receive an `ACTIVE` state at weekly `100%` and can choose it based on reset order or primary availability.

The implementation spans shared quota derivation, dashboard/account summary mapping, proxy state construction, and requested-limit bypass behavior. Existing elapsed-window normalization already prevents an expired sample from pinning an account indefinitely and should remain the recovery mechanism.

## Goals / Non-Goals

**Goals:**

- Derive `QUOTA_EXCEEDED` from a current standard weekly window at `used_percent >= 100` for every account, independent of credit metadata.
- Exclude that state before standard routing strategy or sticky affinity can select it.
- Keep dashboard status and foreground routing aligned.
- Preserve reset-based recovery and operator-disabled states.

**Non-Goals:**

- Making primary/5-hour usage snapshots authoritative before upstream rate-limit evidence.
- Changing independently gated additional-quota eligibility or ranking.
- Persisting a new database field or introducing a migration.
- Changing safe replay rules after downstream-visible output.

## Decisions

1. **Make secondary exhaustion authoritative inside the shared quota helper.** The helper will always derive `QUOTA_EXCEEDED` from `secondary_used >= 100` when inference is enabled, without consulting credit metadata. This keeps account summaries and any inference-enabled call sites consistent.

2. **Enable only secondary inference for foreground proxy state.** Replace the single boolean inference switch with explicit primary and secondary controls. Proxy selection keeps primary snapshots advisory but enables secondary inference, avoiding a blanket reversal of the stale-primary behavior addressed by #1030.

3. **Treat the derived quota state as the common routing guard.** Sticky affinity and every routing strategy already exclude `QUOTA_EXCEEDED`; deriving the state before those paths avoids strategy-specific filters and fixes reset-drain, capacity-weighted, round-robin, and sticky behavior together.

4. **Do not use credit metadata for standard weekly availability.** Credit fields remain exposed for display and accounting but no longer affect standard weekly status. This gives plans that omit credit fields and plans that emit capability-like credit flags identical behavior.

5. **Preserve the independently gated additional-quota exception.** Requested-limit routing already has an explicit `ignore_standard_quota` contract for model-specific entitlements. This change applies to standard routing and does not reinterpret those independent windows.

## Risks / Trade-offs

- **A lagging weekly sample can block an account that upstream has already reset** → Existing reset-deadline normalization and the background post-reset refresh bypass bound this condition; tests will cover elapsed samples.
- **Credit-backed capacity may genuinely work after the weekly percentage reaches 100** → This is an intentional product change: the weekly window, not optional credit metadata, is authoritative.
- **Changing the helper signature can affect many call sites** → Keep backward-compatible defaults and add focused tests for both proxy and summary paths.
- **Persisted account status may remain `active` until an upstream write** → Foreground state and dashboard effective status still become `quota_exceeded`; no persistence migration is required for safe routing.
