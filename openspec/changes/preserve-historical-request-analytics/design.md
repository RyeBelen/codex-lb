## Context

Upstream retention folds additive lifetime usage into `account_usage_rollups`
and `api_key_usage_rollups`, then deletes raw request logs in bounded batches.
Reports, API-key bounded analytics, quota planning, and response-owner lookup
still query raw rows. Production's earlier seven-day prune therefore removed
54,551 rows dated June 12 through July 6 from those surfaces even though
lifetime totals remained correct. A verified pre-prune online SQLite snapshot
contains every missing row, and its 53-column request-log schema exactly matches
the current database.

Exact historical contracts are not all additive. Reports support arbitrary
IANA timezones and DST boundaries, distinct account counts, account/model/user
agent filters, and exact per-day medians. API-key limits use arbitrary half-open
windows and floor cost per request before summing. Previous-response ownership
uses newest-row ordering with API-key and optional session scope.

## Goals / Non-Goals

**Goals:**

- Keep raw request logs at seven days while preserving exact existing Reports,
  dashboard aggregates, API-key windows/trends, quota-planner demand, and
  previous-response ownership indefinitely.
- Preserve upstream lifetime rollups as their existing source of truth.
- Reconstruct all 54,551 recoverable missing rows directly into compact history
  without restoring diagnostic raw logs or double-counting lifetime totals.
- Prove correctness on a cloned production database and an isolated Railway
  staging environment before any production-main rollout.

**Non-Goals:**

- Making request-log list, detail, search, facets, client IPs, error text, or
  other diagnostic fields available beyond raw retention.
- Approximating medians/distinct counts or changing public API schemas.
- Writing snapshot history back into `request_logs`.
- Mutating production or merging the feature branch as part of implementation
  verification.

## Decisions

### Keep additive lifetime rollups plus one compact exact-history fact table

`request_log_history_facts` stores one immutable analytical row per pruned raw
request, keyed by the original request-log id. It contains identity/scope,
timestamp, model/reasoning/service-tier, source/user-agent/request-kind,
status/error code, tokens/cost, and latency/TTFT. It omits raw diagnostics,
free-form text, client IP, proxy endpoint details, and archive metadata.

This is the minimal sufficient statistic for the current exact contracts.
Daily or hourly aggregate-only alternatives cannot compose arbitrary timezone
boundaries, exact medians, exact distinct accounts, arbitrary API-key windows,
or response ownership. Maintaining both dimensional aggregates and facts would
duplicate a source of truth without eliminating the facts, so readers aggregate
the compact facts directly. Upstream lifetime rollups remain the additive layer.

### Project only at prune time, atomically with exact-id deletion

Each retention transaction locks and materializes at most 10,000 deterministic
candidate ids below the existing safe watermark. It inserts facts for those
ids, verifies every candidate is represented, deletes exactly those ids,
verifies delete parity, and commits. Any mismatch rolls back the transaction.

Projection at prune time avoids copying the live tail and needs no second
watermark. A committed row exists in exactly one store. On PostgreSQL candidate
rows and the fold-state row are locked so account lifecycle and fold operations
cannot interleave incorrectly; SQLite uses the existing writer section.

### Use one shared union selectable for historical consumers

A typed helper exposes `UNION ALL` over compact facts and retained raw rows with
identical labeled columns. Every historical reader builds a single SQL statement
from that selectable, so one database snapshot cannot observe a gap or double
count. Request-log diagnostic readers continue to query raw rows only.

The helper is adopted by Reports, dashboard request aggregates, API-key limit
initialization/trends/account-cost views, quota-planner demand bins and warmup
cost reads, and previous-response owner lookup. Fleet pressure keeps using the
raw tail because its longest window is two hours.

### Mirror account lifecycle behavior

Identity consolidation reassigns fact rows with raw logs and lifetime rollups.
Soft account deletion nulls `account_id` and records the same `deleted_at` on
raw and compact rows. Hard history deletion removes compact facts. Owner lookup
retains the current session-first then API-key fallback and only returns a
successful row with a live account id.

### Backfill missing history into facts, never raw logs or lifetime rollups

The backfill command is dry-run by default, accepts an immutable SQLite online
snapshot plus expected SHA-256, validates integrity/schema, and inserts only
source ids absent from both live raw rows and compact facts. It operates in
bounded transactions, emits selected/inserted/skipped/date-range checksums, and
is idempotent: the verified production candidate count is 54,551 on first run
and zero on the second.

Facts are intentionally excluded from upstream lifetime rollup folding and
summary tail queries, so importing them cannot double-count the already-imported
lifetime totals. Snapshot rows whose account no longer exists are not restored;
the verified source currently has zero such rows.

### Verify locally and on an isolated Railway environment

Local verification migrates a current production online-backup clone, attaches
the pre-prune snapshot, runs backfill, and compares raw-plus-fact results with
snapshot truth across timezones, filters, medians, cost rounding, quota bins,
owner scoping, and account lifecycle. It then prunes with a seven-day cutoff and
proves every historical result remains unchanged.

Only committed/pushed branch code may be deployed to a duplicated Railway
staging environment with a separate volume. Staging disables schedulers while
seeding, has no public domain, and never mounts the production volume. After
backfill parity, retention is set to seven days and run twice; the second pass
must be empty. Production `main` remains untouched pending explicit approval.

## Risks / Trade-offs

- [Compact history still grows one row per request] -> It stores roughly 257
  bytes of selected payload per sampled row; budget 0.5-1.0 KiB including tuple
  and indexes, monitor size, and revisit columnar archival only at much larger
  scale.
- [A projection bug could delete unrepresented history] -> Count parity and one
  transaction fail closed, retaining raw rows on any error.
- [Reader conversion could silently miss one consumer] -> Central inventory and
  raw-prune parity tests cover Reports, API keys, quota planner, dashboard, and
  owner lookup; repository-wide `RequestLog` searches remain a verification
  gate.
- [Snapshot backfill could resurrect intentionally purged history] -> Exclude
  absent accounts and validate account/delete state before insertion.
- [Staging could accidentally run production schedulers or share storage] ->
  duplicate configuration only, create a new volume, scale to zero while
  seeding, disable schedulers, and verify volume ids before startup.

## Migration Plan

1. Add the fact schema and indexes with a single forward Alembic revision.
2. Implement atomic projection, shared readers, lifecycle updates, and dry-run
   backfill tooling on the feature branch.
3. Rehearse migration/backfill/prune twice on cloned production data and record
   integrity, count, checksum, query parity, and storage evidence.
4. Commit and push the branch; deploy it to isolated Railway staging with a
   cloned database and retention initially disabled.
5. Verify API/dashboard parity, set staging retention to seven days, run prune,
   and repeat parity plus live request smoke tests.
6. Present evidence for explicit production approval. Before production, take
   a fresh online backup; rollback always restores matching code and database.

## Open Questions

- None blocking implementation. Retention stays unchanged in production until
  staging evidence is accepted.

