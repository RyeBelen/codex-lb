## ADDED Requirements

### Requirement: Persist per-account weekly-empty reset preference
The database SHALL persist non-null Boolean `accounts.auto_redeem_reset_credits_when_weekly_exhausted` defaulting false for existing and new accounts. Its migration SHALL extend the current single head and support downgrade and upgrade without changing other data. Reimports SHALL preserve an existing account opt-in. The existing account PATCH SHALL update requested preferences atomically and audit the field in account_updated.changed_fields. Unspecified account fields SHALL remain unchanged; absent or pending-deletion accounts SHALL remain not found.

#### Scenario: Upgrade an existing installation
- **WHEN** the migration is applied
- **THEN** existing accounts retain all data and the new preference is false
