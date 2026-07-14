## ADDED Requirements

### Requirement: Compact facts preserve exact historical request semantics

The system MUST retain one compact historical fact for every pruned raw request
log. Facts MUST preserve the original request-log id and every field required
by historical reports, bounded API-key accounting, quota planning, and scoped
previous-response ownership. Facts MUST NOT make pruned raw rows visible through
request-log list, detail, search, or facet APIs.

#### Scenario: Pruned request remains analytically visible

- **WHEN** a raw request row crosses the retention cutoff
- **THEN** its compact fact contributes to every applicable historical consumer
- **AND** its diagnostic request-log row is no longer listable or retrievable

### Requirement: Historical readers combine facts and raw tail exactly once

Historical readers MUST query compact facts and retained raw rows in one
database statement and snapshot. A committed request id MUST exist in only one
of those stores, and readers MUST preserve the current filtering, ordering,
rounding, timezone, distinct-count, and median semantics.

#### Scenario: Query crosses the raw retention boundary

- **GIVEN** qualifying requests exist in compact history and the raw tail
- **WHEN** a historical query spans both stores
- **THEN** every qualifying request contributes exactly once
- **AND** the result equals the same query before pruning

### Requirement: Account lifecycle applies to compact history

Account identity consolidation, soft deletion, and hard history deletion MUST
apply to compact facts with the same attribution semantics as raw request logs.

#### Scenario: Account is consolidated

- **WHEN** duplicate accounts are consolidated into a canonical account
- **THEN** matching compact facts are reassigned to the canonical account in the
  same serialized operation as raw logs and lifetime rollups

#### Scenario: Account history is deleted

- **WHEN** an account is deleted with history purge enabled
- **THEN** matching compact facts are removed

#### Scenario: Account is soft deleted

- **WHEN** an account is deleted without history purge
- **THEN** matching compact facts set `account_id` to null and record the same
  deletion timestamp as matching raw rows

### Requirement: Snapshot backfill is verified and idempotent

The backfill tool MUST be dry-run by default and MUST validate the source
snapshot checksum, SQLite integrity, and request-log schema before writing. It
MUST insert only source ids absent from both current raw logs and compact facts,
operate in bounded transactions, report count/date/checksum evidence, and make
a successful second run insert zero rows. It MUST NOT change lifetime rollups or
their watermark.

#### Scenario: Missing production history is reconstructed

- **GIVEN** the verified pre-prune snapshot and current production clone
- **WHEN** backfill runs in apply mode
- **THEN** exactly 54,551 missing facts dated June 12 through July 6 are inserted
- **AND** no newer raw request is overwritten
- **AND** lifetime rollups and their watermark are unchanged

#### Scenario: Backfill is repeated

- **GIVEN** a completed successful backfill
- **WHEN** the same snapshot is backfilled again
- **THEN** zero facts are inserted

