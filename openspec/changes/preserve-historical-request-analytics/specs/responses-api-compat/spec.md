## ADDED Requirements

### Requirement: Raw retention preserves scoped previous-response ownership

Previous-response owner lookup MUST search compact facts and retained raw rows
in one snapshot. It MUST preserve API-key scope, prefer a supplied matching
session, order candidates by newest `requested_at` then original request-log id,
and return only a successful candidate with a live account id.

#### Scenario: Owner row has been compacted

- **WHEN** a follow-up references a successful response whose owner row crossed raw retention
- **THEN** lookup returns the same scoped owner account as before pruning

#### Scenario: Session-specific candidate exists in either store

- **WHEN** owner candidates span compact history and raw tail and a session id is supplied
- **THEN** the newest matching-session live owner is preferred across both stores
- **AND** unscoped fallback occurs only when no scoped live owner is found

