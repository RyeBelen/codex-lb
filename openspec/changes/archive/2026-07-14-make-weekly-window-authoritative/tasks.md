## 1. Shared quota semantics

- [x] 1.1 Remove credit-metadata overrides from current standard weekly-window exhaustion while preserving operator-disabled states and reset recovery.
- [x] 1.2 Add separate primary and weekly inference controls so foreground routing keeps primary snapshots advisory but treats weekly snapshots as authoritative.

## 2. Proxy and dashboard behavior

- [x] 2.1 Apply authoritative weekly inference before standard sticky affinity and routing-strategy selection while retaining the independently gated additional-quota bypass.
- [x] 2.2 Keep account/dashboard effective status aligned with the shared weekly rule for missing, zero, positive, and unlimited credit metadata.

## 3. Regression coverage

- [x] 3.1 Update shared quota and account-mapper tests that previously expected credit-backed weekly exhaustion to remain active.
- [x] 3.2 Add or update standard routing regressions for reset-drain, earlier-reset capacity selection, sticky affinity, and elapsed weekly recovery.
- [x] 3.3 Add dashboard integration coverage proving weekly exhaustion remains `quota_exceeded` with primary capacity and credit metadata.
- [x] 3.4 Verify independently gated additional-quota routing retains its existing standard-quota bypass.

## 4. Validation

- [x] 4.1 Run focused unit and integration tests for quota derivation, proxy routing, stickiness, and dashboard status.
- [x] 4.2 Run formatting/lint checks and strict OpenSpec validation.
