## 1. Schema and shared history source

- [x] 1.1 Add typed compact historical-fact ORM metadata and a single-head Alembic migration with evidence-based indexes
- [x] 1.2 Add one reusable raw-plus-fact selectable with identical typed columns and no diagnostic-list integration
- [ ] 1.3 Add SQLite/PostgreSQL migration, drift, and query-plan coverage

## 2. Atomic retention and lifecycle

- [x] 2.1 Lower the validated raw request-log retention floor to seven days while keeping zero disabled
- [x] 2.2 Lock fold state and deterministic candidate rows, project each bounded batch, verify selected/projected/deleted parity, and commit atomically
- [x] 2.3 Mirror account consolidation, soft deletion, and hard history deletion into compact facts under existing serialization
- [x] 2.4 Add failure-injection, multi-batch, no-watermark, stale-watermark, and lifecycle tests

## 3. Historical consumers

- [x] 3.1 Convert dashboard request aggregates, activity, top-error, earliest-activity, and owner lookup to the shared history source while leaving raw diagnostics unchanged
- [x] 3.2 Convert all Reports queries and prove timezone, DST/non-hour offset, filters, distinct accounts, and odd/even exact median parity
- [x] 3.3 Convert API-key limit initialization, trends/totals, and account-cost views with exact existing filtering and per-request rounding
- [x] 3.4 Convert quota-planner warmup-cost and 15-minute demand reads while leaving short-window fleet pressure raw-only

## 4. Missing-history recovery

- [x] 4.1 Add a dry-run-default, checksum/integrity/schema-verified SQLite snapshot backfill command with bounded idempotent inserts
- [x] 4.2 Prove the production candidate set is exactly 54,551 missing ids from June 12 through July 6 with no absent-account resurrection
- [x] 4.3 Prove first-run insertion, zero-row second run, unchanged lifetime rollups/watermark, and exact snapshot parity

## 5. Local production-clone verification

- [x] 5.1 Migrate and backfill cloned current/pre-prune production snapshots and record integrity, counts, checksums, query parity, and storage evidence
- [x] 5.2 Run a seven-day prune twice on the clone and prove historical results remain unchanged and the second pass is empty
- [x] 5.3 Run strict OpenSpec validation, lint, scoped type checks, targeted suites, and the container frontend build; record unrelated baseline suite blockers

## 6. Isolated Railway staging

- [x] 6.1 Commit focused changes and push only the feature branch
- [x] 6.2 Create a duplicated-config staging environment with a separate environment volume instance, standard authentication, and production-affecting schedulers disabled
- [x] 6.3 Deploy and migrate the feature branch against a disposable staging database without touching production storage
- [x] 6.4 Verify aggregate parity, enable seven-day staging retention, prune twice, redeploy, and pass health checks
- [x] 6.5 Record staging evidence and a backup/rollback production plan before merging or deploying production main
