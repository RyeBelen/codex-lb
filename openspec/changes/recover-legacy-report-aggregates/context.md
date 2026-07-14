## Purpose and scope

This change recovers the last surviving dated dimensions for requests that were
already compacted before the exact historical-fact system existed. The verified
source contains 1,043 aggregate rows representing 23,080 requests from
2026-04-24 through 2026-06-11. Exact request-level history begins on 2026-06-12.

## Decision rationale

The legacy rows are preserved in a dedicated immutable archive. They are not
converted into synthetic request facts because one aggregate row can represent
many requests and carries no request id, session id, precise timestamp, or
per-request latency distribution. They are not imported into lifetime rollups
because the upstream migration already imported those totals.

The archive is included only when Reports is evaluated in UTC. Its
`bucket_date` is a whole UTC day and cannot be split across Asia/Manila,
America/New_York, DST, or partial-day boundaries without inventing data. The UI
therefore offers an explicit recovered-history UTC mode instead of silently
mixing local and UTC buckets.

## Exact supported data

For whole UTC days the archive preserves requests, errors, input/output/cached
tokens, cost, distinct account ids, and cost/request breakdowns by model,
account, and user-agent group. Existing warmup exclusions and missing
user-agent grouping still apply.

## Unsupported data and failure modes

- Median TTFT and median TPS are unavailable for aggregate-only days because
  sums and counts cannot reconstruct a distribution.
- Request-log detail, search, previous-response ownership, and session
  continuity cannot use the archive.
- Non-UTC report mode must advertise available recovered coverage but must not
  include aggregate buckets.
- Import must fail on source hash, revision, schema, count, aggregate-key hash,
  totals, overlap, or integrity mismatch.
- Re-import must select zero rows and must never change lifetime rollups.

For example, TTFT samples `[1, 1, 7]` and `[2, 3, 4]` both have sum 9 and count
3 but different medians. The UI must show the speed metric as unavailable for
that recovered day, not as a measured zero.

## Operational notes

The immutable source is
`store.pre-prune-20260714T012557Z.db`, SHA-256
`f6f0d2d3a508f9dab3a8ab6556d031fc12e0bbafc948394aa8c2995367089d61`.
The import target is exactly 1,043 rows and 23,080 requests. Production rollout
requires a fresh online backup, a clone rehearsal, an isolated Railway staging
deployment, an idempotency rerun, and report parity evidence.

