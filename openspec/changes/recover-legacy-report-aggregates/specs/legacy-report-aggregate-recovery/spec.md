## ADDED Requirements

### Requirement: Legacy report aggregates are imported from a verified snapshot

The system MUST provide a dry-run-default import that accepts an immutable
SQLite snapshot only after verifying its SHA-256, integrity, migration revision,
required schema, expected aggregate-row count, aggregate-key checksum, expected
measure totals, and date range. Apply mode MUST insert only absent aggregate
keys in bounded transactions and MUST be idempotent.

#### Scenario: Verified legacy history is imported once

- **GIVEN** a verified snapshot containing legacy daily aggregates disjoint from exact history
- **WHEN** the operator applies the import with matching checksums and totals
- **THEN** every expected aggregate row is inserted into the legacy archive
- **AND** lifetime rollups, raw request logs, and compact facts are unchanged
- **AND** a second dry run selects zero rows

#### Scenario: Overlapping history is rejected

- **GIVEN** a source aggregate bucket overlaps the UTC date range represented by raw request logs or compact facts
- **WHEN** the operator runs the import
- **THEN** the import fails before writing any archive row

### Requirement: Legacy aggregate storage remains separate and immutable

The system MUST store imported legacy aggregate rows separately from raw request
logs, compact historical facts, and lifetime rollups. The retention scheduler
MUST NOT create, update, or delete legacy aggregate rows.

#### Scenario: Future pruning does not mutate recovered aggregates

- **WHEN** request-log retention projects and deletes an exact raw batch
- **THEN** the legacy aggregate archive remains byte-for-byte unchanged

### Requirement: Reports include legacy aggregates only with exact UTC semantics

Reports MUST merge legacy aggregates with exact raw-plus-fact history only when
the resolved report timezone is UTC. The merge MUST preserve request, error,
token, cost, model, account, and user-agent totals for whole UTC buckets and
MUST deduplicate active account ids across sources.

#### Scenario: UTC report includes recovered additive history

- **GIVEN** a UTC report range overlaps legacy aggregate buckets and exact history
- **WHEN** Reports computes summary, daily, model, account, and user-agent results
- **THEN** supported additive values equal the disjoint sum of both sources
- **AND** an account present in both sources counts once in active-account totals

#### Scenario: Non-UTC report does not misallocate legacy buckets

- **GIVEN** a report uses Asia/Manila or a DST-observing timezone
- **WHEN** its range overlaps legacy UTC buckets
- **THEN** the report excludes legacy aggregates from computed values
- **AND** coverage metadata advertises that recovered UTC history is available

### Requirement: Aggregate-only limitations are explicit

Reports MUST expose legacy coverage metadata including availability, inclusion,
UTC date range, aggregate-row count, request count, and unsupported metrics.
Aggregate-only daily rows MUST identify their resolution and MUST represent
median TTFT and median TPS as unavailable rather than measured zero.

#### Scenario: Dashboard distinguishes recovered aggregate days

- **WHEN** a UTC report includes an aggregate-only day
- **THEN** the API marks that day as aggregate-only
- **AND** the dashboard shows a recovered-history notice
- **AND** speed charts render unavailable aggregate-only samples as gaps

