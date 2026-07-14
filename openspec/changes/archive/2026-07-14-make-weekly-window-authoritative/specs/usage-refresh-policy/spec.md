## ADDED Requirements

### Requirement: Current weekly quota exhaustion is credit-independent

When account status is derived from standard usage snapshots, a current standard secondary/weekly window at `used_percent >= 100` MUST derive `quota_exceeded`. The result MUST be identical when credit metadata is missing, `credits_has` is true or false, `credits_unlimited` is true or false, or `credits_balance` is zero or positive. An available primary/5-hour window MUST NOT override the exhausted weekly window. Paused, deactivated, and reauthentication-required states MUST remain preserved.

#### Scenario: Weekly exhaustion without credit fields derives quota exceeded

- **GIVEN** an otherwise active account whose current weekly usage reports `used_percent >= 100`
- **AND** its usage samples do not report credit metadata
- **WHEN** account-summary or proxy status is derived
- **THEN** the effective status is `quota_exceeded`

#### Scenario: Weekly exhaustion with credit fields derives quota exceeded

- **GIVEN** an otherwise active account whose current weekly usage reports `used_percent >= 100`
- **AND** its newest usage sample reports any combination of credit flags or balance
- **WHEN** account-summary or proxy status is derived
- **THEN** the effective status is `quota_exceeded`

#### Scenario: Available primary window does not override weekly exhaustion

- **GIVEN** an otherwise active account whose primary usage is below 100 percent
- **AND** its current weekly usage is at least 100 percent
- **WHEN** effective status is derived
- **THEN** the effective status is `quota_exceeded`

#### Scenario: Operator-disabled states remain preserved

- **GIVEN** an account is paused, deactivated, or reauthentication-required
- **AND** its current weekly usage is exhausted
- **WHEN** effective status is derived
- **THEN** the operator or authentication state is preserved

## REMOVED Requirements

### Requirement: Credit-backed secondary quota remains usable

**Reason**: Credit metadata is not consistently present across plans and can describe credit capability even when no usable balance is shown. It must no longer override the account-wide weekly window.

**Migration**: Use `Current weekly quota exhaustion is credit-independent`; credit fields remain informational and do not affect standard weekly status.

### Requirement: Credit-backed usage remains selectable after quota windows fill

**Reason**: Allowing credit metadata to reactivate a weekly-exhausted account contradicts the weekly-window-authoritative routing contract and caused upstream usage-limit failures.

**Migration**: Treat a current weekly window at or above 100 percent as `quota_exceeded` regardless of credit metadata. Primary exhaustion retains its existing behavior only while weekly capacity remains available.
