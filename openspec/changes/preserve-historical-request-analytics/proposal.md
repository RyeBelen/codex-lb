## Why

Upstream retention preserves lifetime account and API-key totals, but pruning
raw `request_logs` removes the row-level dimensions required by Reports,
bounded API-key analytics, and previous-response ownership. Production already
lost 54,551 raw rows from June 12 through July 6, so the new historical system
must also reconstruct those contracts from the verified pre-prune snapshot.

## What Changes

- Add compact historical request facts that preserve exact non-additive
  analytics and continuity fields while omitting raw diagnostic payloads.
- Materialize compact facts atomically before every bounded raw-log deletion,
  with selected/projected/deleted row-count parity and fail-closed rollback.
- Make report, dashboard aggregate, API-key window/trend, and response-owner
  readers combine compact history with the retained raw tail exactly once.
- Mirror account reassignment, soft deletion, and hard history deletion into
  compact history.
- Add an idempotent, checksummed backfill workflow that reconstructs all
  recoverable production history from a SQLite online snapshot without
  overwriting newer traffic or double-counting lifetime rollups.
- Require local production-clone parity tests and an isolated Railway staging
  deployment before any production-main rollout.

## Capabilities

### New Capabilities

- `historical-request-analytics`: Compact exact-history persistence, atomic
  projection, lifecycle behavior, snapshot backfill, and parity verification.

### Modified Capabilities

- `data-retention`: Raw pruning must preserve every historical consumer rather
  than intentionally truncating reports and owner lookup.
- `proxy-runtime-observability`: Reports and dashboard aggregates must read
  compact history plus the raw tail with exact existing semantics.
- `api-keys`: Historical limit initialization, trends, and account-cost views
  must survive raw retention.
- `responses-api-compat`: Previous-response owner lookup must survive raw-row
  pruning without weakening API-key/session scoping.
- `quota-phase-planner`: Historical demand bins and warmup-cost observations
  must remain complete when their 28-day window crosses raw retention.
- `database-migrations`: Schema and snapshot backfill must be forward-only,
  idempotent, integrity-checked, and safe on SQLite and PostgreSQL.

## Impact

Affected areas include ORM/Alembic schema, the upstream retention job, request
log/report/API-key/account repositories, continuity owner lookup, test fixtures,
and Railway rollout operations. Public API shapes remain unchanged. Production
`main` and its database are explicitly out of scope until staging evidence is
accepted.
