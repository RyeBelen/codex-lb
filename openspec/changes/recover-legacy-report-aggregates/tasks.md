## 1. Schema and import

- [ ] 1.1 Add typed immutable legacy aggregate ORM metadata and a single-head Alembic migration for SQLite and PostgreSQL
- [ ] 1.2 Add a dry-run-default snapshot import with source hash/schema/integrity, aggregate-key, totals, date-boundary, and idempotency verification
- [ ] 1.3 Add migration, import failure, overlap rejection, and second-run-zero coverage

## 2. Reports backend

- [ ] 2.1 Add typed coverage metadata and aggregate-only daily resolution to the Reports contract
- [ ] 2.2 Merge exact additive summary/daily/model/account/user-agent metrics only in UTC mode without double-counting active accounts
- [ ] 2.3 Keep non-UTC reports exact-history-only while advertising available legacy coverage; keep aggregate-only medians unavailable
- [ ] 2.4 Add repository/service/API regression coverage for filters, warmups, missing user agents, UTC, Manila, and DST timezones

## 3. Reports frontend

- [ ] 3.1 Parse coverage/resolution metadata and offer explicit recovered-history UTC mode when the selected range overlaps legacy coverage
- [ ] 3.2 Label aggregate-only coverage and render unavailable speed samples as gaps rather than zero
- [ ] 3.3 Add frontend contract, page interaction, daily table/export, and chart regression tests

## 4. Verification and rollout

- [ ] 4.1 Run strict OpenSpec validation where available, lint, type checks, focused backend suites, frontend tests, and production build
- [ ] 4.2 Rehearse the verified 1,043-row/23,080-request import on a production clone and prove exact totals, disjointness, unchanged lifetime rollups, and second-run zero
- [ ] 4.3 Commit and push focused changes; deploy only to isolated Railway staging with separate storage
- [ ] 4.4 Verify staging migration/import/UTC reports/non-UTC exclusion/redeploy/health and record evidence before production approval

