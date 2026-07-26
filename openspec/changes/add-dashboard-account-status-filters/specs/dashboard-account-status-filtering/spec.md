## ADDED Requirements

### Requirement: Dashboard account cards support status filtering
The dashboard account-card view SHALL provide a multi-select status filter and SHALL render only accounts whose raw status is selected.

#### Scenario: Initial account-card filter
- **WHEN** the dashboard loads accounts with active, paused, rate-limited, quota-exceeded, re-auth-required, and deactivated statuses
- **THEN** active, paused, rate-limited, and quota-exceeded accounts are selected and visible by default
- **AND** re-auth-required and deactivated accounts are available as choices but hidden by default

#### Scenario: Account-card status selection changes
- **WHEN** an operator selects or clears a status in the account-card filter
- **THEN** the account-card grid updates without changing any account status on the server

### Requirement: Dashboard usage charts support status filtering
The dashboard usage view SHALL provide a multi-select status filter and SHALL include only selected account statuses in both five-hour and weekly charts.

#### Scenario: Filtered chart values remain consistent
- **WHEN** an operator excludes one or more account statuses from the usage filter
- **THEN** each chart's segments, total capacity, and center remaining-credit value are calculated from the same visible account subset

#### Scenario: Independent dashboard filters
- **WHEN** an operator changes the usage-chart status filter
- **THEN** the account-card filter selection remains unchanged

### Requirement: Status filters use localized accessible labels
Dashboard status filters SHALL use the existing localized dashboard filter label and localized account-status vocabulary, with a readable fallback for unknown statuses.

#### Scenario: Known status localization
- **WHEN** a known account status is presented as a filter option
- **THEN** its label uses the active locale's `common.status` translation

#### Scenario: Future status fallback
- **WHEN** an account reports a status that has no known normalized translation
- **THEN** the filter presents a human-readable label derived from the raw status and remains functional
