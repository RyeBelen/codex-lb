## Context

Current Reports uses one exact `UNION ALL` over compact facts and retained raw
rows. That source recovers all 97,591 request ids present in the pre-prune raw
snapshot. A separate retired table in the same snapshot contains the only dated
dimensions for 23,080 older requests. Its buckets are disjoint from exact
history: legacy ends 2026-06-11 and exact history starts 2026-06-12.

## Goals / Non-Goals

**Goals:**

- Preserve and import the verified legacy aggregate rows without double count.
- Restore exact additive Reports totals and supported breakdowns for UTC days.
- Make coverage and precision visible to API and dashboard users.
- Keep snapshot import dry-run-first, checksummed, bounded, and idempotent.

**Non-Goals:**

- Reconstructing request ids, sessions, timestamps, ownership, or diagnostics.
- Estimating medians, TPS distributions, or local-time bucket allocation.
- Reintroducing aggregate generation for future pruning.
- Modifying already-correct lifetime rollups.

## Decisions

### Store retired rows in an immutable archive table

`request_log_legacy_daily_aggregates` preserves the retired schema fields needed
by Reports and uses `aggregate_key` as its stable primary identity. It has no
relationship to the exact request-fact primary key and is never written by the
retention job.

### Verify import against source identity and aggregate totals

The CLI attaches an immutable SQLite source read-only, verifies SHA-256,
`quick_check`, Alembic revision, required columns, expected row count,
aggregate-key SHA-256, request/token/cost totals, and date range. It rejects any
source bucket whose date overlaps exact raw/fact history, then inserts absent
aggregate keys in bounded transactions. The second run must select zero.

### Merge only in explicit UTC report mode

Repository aggregate functions merge legacy rows with exact history only when
the resolved report timezone is UTC. Summary active accounts use a distinct
union of account ids instead of adding counts. Daily additive rows merge by UTC
date. Model/account/user-agent rows merge by their dimension key. Aggregate-only
daily rows carry a distinct resolution marker and nullable speed medians.

### Expose coverage metadata and a visible UI mode

Every Reports response exposes whether legacy coverage is available, whether it
was included, its UTC date range, row/request counts, and limitations. When a
selected range overlaps available legacy history in a non-UTC report, the UI
offers a control to switch the report query to UTC. Included mode shows a clear
aggregate-only notice and gaps speed charts for aggregate-only days.

## Risks / Trade-offs

- [Users may mistake aggregate history for request detail] -> coverage metadata,
  per-day resolution, and UI notices state the limitation.
- [UTC mode changes recent-day boundaries] -> inclusion is explicit and the UI
  labels the active UTC mode.
- [Old aggregate rows could double count exact facts] -> import rejects date
  overlap and the verified production boundary is fixed between June 11/12.
- [Float cost drift] -> preserve integer microdollars and use it for exact sums;
  retain legacy float only for compatibility checks.

## Migration and rollout

1. Add the archive table and indexes with a forward Alembic revision.
2. Add import CLI, Reports read path, API coverage metadata, and UI mode.
3. Rehearse on production clones and prove expected totals and second-run zero.
4. Commit/push and validate in credential-free GitHub CI, including Docker
   build, SQLite/PostgreSQL migration checks, and backend/frontend suites.
5. Verify the production clone locally without starting a second service that
   contains copied production accounts, schedulers, or upstream credentials.
6. Only after explicit acceptance, merge through repository gates and perform a
   fresh-backup production import.
