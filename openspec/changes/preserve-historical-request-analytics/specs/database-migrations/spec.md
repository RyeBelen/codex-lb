## ADDED Requirements

### Requirement: Compact history schema upgrades through one Alembic head

The database schema MUST create compact historical facts and required lookup
indexes through a forward Alembic revision on the current single head. ORM
metadata and migration schema MUST match on SQLite and PostgreSQL, and startup
drift detection MUST pass.

#### Scenario: Existing database upgrades

- **WHEN** a current database upgrades to head
- **THEN** compact fact storage and indexes exist
- **AND** existing raw rows and lifetime rollups remain unchanged
- **AND** migration policy and schema drift checks pass

### Requirement: Production recovery is proven outside production

The feature branch MUST pass a production-clone migration/backfill/prune
rehearsal and an isolated Railway staging deployment on a separate volume before
production-main rollout. Evidence MUST include source checksum, integrity,
candidate/insert/idempotency counts, cross-consumer query parity, storage size,
health, and live request smoke tests.

#### Scenario: Staging proves restored history and seven-day pruning

- **WHEN** staging is seeded from production snapshots and backfilled
- **THEN** the first backfill inserts exactly 54,551 facts and the second inserts zero
- **AND** historical consumer results match snapshot truth
- **WHEN** staging retention prunes to seven days
- **THEN** those results remain unchanged and health/live request checks pass

