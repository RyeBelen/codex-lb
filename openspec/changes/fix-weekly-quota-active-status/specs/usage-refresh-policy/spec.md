## ADDED Requirements

### Requirement: Exhausted weekly quota is unavailable

When an account's authoritative weekly usage window reports `used_percent >= 100`, the system MUST derive the account as `quota_exceeded` regardless of `credits_has`, `credits_unlimited`, or `credits_balance` metadata. Proxy account selection and account/dashboard summary mapping MUST use the same effective status. Explicit `paused`, `deactivated`, and `reauth_required` states MUST remain unchanged.

#### Scenario: Weekly exhaustion overrides credit metadata

- **GIVEN** an otherwise routable account whose weekly usage reports `used_percent >= 100`
- **AND** the latest usage sample reports `credits_has = true`, `credits_unlimited = true`, or a positive `credits_balance`
- **WHEN** the system derives the account's effective status
- **THEN** the effective status is `quota_exceeded`
- **AND** the account is unavailable for proxy selection

#### Scenario: Dashboard count matches routable weekly capacity

- **GIVEN** an account whose short-window usage is below `100`
- **AND** its weekly usage reports `used_percent >= 100`
- **WHEN** the dashboard renders account summaries
- **THEN** the account is not counted as active
- **AND** its summary status is `quota_exceeded`

#### Scenario: Weekly capacity restores availability

- **GIVEN** an account previously derived as `quota_exceeded` from weekly exhaustion
- **AND** its authoritative weekly usage now reports `used_percent < 100`
- **WHEN** the system derives the account's effective status after the reset
- **THEN** the weekly exhaustion no longer prevents the account from becoming active

#### Scenario: Explicitly unavailable states remain unavailable

- **GIVEN** an account is `paused`, `deactivated`, or `reauth_required`
- **AND** its weekly usage reports `used_percent < 100`
- **WHEN** the system derives the account's effective status
- **THEN** the explicit unavailable state is preserved

## REMOVED Requirements

### Requirement: Credit-backed secondary quota remains usable

**Reason**: Credit capability metadata can remain true when the recorded balance is zero and does not prove that an exhausted weekly allowance can accept traffic.

**Migration**: Determine weekly availability from the authoritative weekly usage percentage; accounts recover after a later sample reports less than 100 percent used.

### Requirement: Credit-backed usage remains selectable after quota windows fill

**Reason**: Selecting accounts after their authoritative weekly window reaches 100 percent makes routing availability disagree with actual upstream capacity and with the operator's expected active count.

**Migration**: Exclude weekly-exhausted accounts from selection and use the same derived `quota_exceeded` status in account and dashboard responses.
