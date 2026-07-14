## Verification evidence

### Verified production source

- Snapshot: `store.pre-prune-20260714T012557Z.db`
- SHA-256: `f6f0d2d3a508f9dab3a8ab6556d031fc12e0bbafc948394aa8c2995367089d61`
- Source revision: `20260714_000000_harden_request_log_rollup_parity`
- Source quick check: `ok`
- Aggregate rows: 1,043
- Aggregate-key SHA-256: `4a9367861011a338a230db69dab98671530051fdda14a2f1fa300fd6d6091400`
- UTC bucket range: 2026-04-24 through 2026-06-11
- Requests represented: 23,080
- Errors: 327
- Input/output/cached/reasoning tokens: 2,571,346,430 / 10,589,804 / 2,322,087,552 / 3,067,983
- Cost microdollars: 1,721,491,800

### Production-clone rehearsal

- Migrated clone from `20260714_020000_add_request_log_historical_facts` to
  `20260714_030000_add_request_log_legacy_daily_aggregates`.
- `codex-lb-db check`: `migration_policy=ok`, `schema_drift=none`.
- Dry run selected 1,043 candidates; apply inserted 1,043; second dry run
  selected zero.
- Source minus archive: zero rows; archive minus source: zero rows.
- Legacy versus raw UTC-day overlap: zero; legacy versus compact-fact UTC-day
  overlap: zero.
- SQLite `quick_check=ok`; foreign-key violations: zero.
- Raw rows stayed 45,023 and compact facts stayed 54,551.
- Account/API-key lifetime rollup row counts, requests, tokens, and cost were
  unchanged before and after import.
- UTC report from April 24 through July 14 returned 122,410 requests; all 41
  aggregate-only activity days carried `historyResolution=legacy_aggregate`
  with nullable speed medians. Asia/Manila excluded legacy buckets and exposed
  available coverage metadata.

### Automated checks

- Backend Ruff: pass.
- Scoped backend `ty`: pass. Full-tree `ty` has the existing optional
  `prometheus_client` unresolved-import diagnostic outside this change.
- Reports unit/integration/API: 41 passed.
- Recovery/migration/CLI plus retention/history focus: 81 passed, one
  PostgreSQL-only test skipped locally because no PostgreSQL test URL was set.
- Frontend Reports Vitest: 12 files, 88 tests passed.
- Frontend TypeScript, Reports ESLint, and production build: pass.
- OpenSpec CLI was unavailable in the local shell; artifact structure and
  normative/context separation were checked directly.

### Isolation decision

A duplicated Railway environment was created but its deployment was stopped
while still building, then the environment was deleted before it could run.
Production remained on deployment `74341c34` from `main`; no production source,
variables, volume, or deployment changed. Further pre-production validation uses
the production clone plus credential-free GitHub CI so no copied service can
call or compete with live upstream APIs.

Production remains unchanged. Final GitHub CI is still required.
