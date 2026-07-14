## 1. Schema and shared history source

- [ ] 1.1 Add typed compact historical-fact ORM metadata and a single-head Alembic migration with evidence-based indexes
- [ ] 1.2 Add one reusable raw-plus-fact selectable with identical typed columns and no diagnostic-list integration
- [ ] 1.3 Add SQLite/PostgreSQL migration, drift, and query-plan coverage

## 2. Atomic retention and lifecycle

- [ ] 2.1 Lower the validated raw request-log retention floor to seven days while keeping zero disabled
- [ ] 2.2 Lock fold state and deterministic candidate rows, project each bounded batch, verify selected/projected/deleted parity, and commit atomically
- [ ] 2.3 Mirror account consolidation, soft deletion, and hard history deletion into compact facts under existing serialization
- [ ] 2.4 Add retry, failure-injection, multi-batch, no-watermark, stale-watermark, and concurrent lifecycle tests

## 3. Historical consumers

- [ ] 3.1 Convert dashboard request aggregates, activity, top-error, earliest-activity, and owner lookup to the shared history source while leaving raw diagnostics unchanged
- [ ] 3.2 Convert all Reports queries and prove timezone, DST/non-hour offset, filters, distinct accounts, and odd/even exact median parity
- [ ] 3.3 Convert API-key limit initialization, trends/totals, and account-cost views with exact existing filtering and per-request rounding
- [ ] 3.4 Convert quota-planner warmup-cost and 15-minute demand reads while leaving short-window fleet pressure raw-only

## 4. Missing-history recovery

- [ ] 4.1 Add a dry-run-default, checksum/integrity/schema-verified SQLite snapshot backfill command with bounded idempotent inserts
- [ ] 4.2 Prove the production candidate set is exactly 54,551 missing ids from June 12 through July 6 with no absent-account resurrection
- [ ] 4.3 Prove first-run insertion, zero-row second run, unchanged lifetime rollups/watermark, and cross-consumer snapshot parity

## 5. Local production-clone verification

- [ ] 5.1 Migrate and backfill cloned current/pre-prune production snapshots and record integrity, counts, checksums, query parity, and storage evidence
- [ ] 5.2 Run a seven-day prune twice on the clone and prove historical results remain unchanged and the second pass is empty
- [ ] 5.3 Run strict OpenSpec validation, lint, type checks, targeted suites, full backend tests, and frontend tests/build

## 6. Isolated Railway staging

- [ ] 6.1 Commit focused changes and push only the feature branch
- [ ] 6.2 Create a duplicated-config staging environment with a distinct volume, no public domain, and schedulers disabled while seeding
- [ ] 6.3 Seed staging from an online production clone, deploy the feature branch, migrate, and backfill without touching production storage
- [ ] 6.4 Verify report/dashboard/API-key/quota/owner parity, enable seven-day staging retention, prune twice, and run health plus live request smoke tests
- [ ] 6.5 Present staging evidence and a backup/rollback production plan without merging or deploying production main
