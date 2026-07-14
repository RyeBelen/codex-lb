## Why

The compact-history recovery restored every raw request available in the
pre-prune snapshot, but 23,080 older requests from April 24 through June 11
survive only as 1,043 retired daily aggregate rows. Upstream migration imported
their lifetime totals and then removed the dimensional aggregate table, so the
Reports timeline still omits almost seven weeks of recoverable activity.

## What Changes

- Add an immutable legacy daily-aggregate archive that is separate from raw
  request logs, compact request facts, and lifetime rollups.
- Add a dry-run-default, checksum-verified, idempotent snapshot import that
  accepts only aggregate buckets disjoint from raw and compact history.
- Include the archive in Reports only under exact UTC-bucket semantics.
- Expose report coverage metadata and a Reports UI control that clearly labels
  aggregate-only history and switches the report to UTC when included.
- Keep per-request diagnostics, response ownership, arbitrary API-key windows,
  and median speed metrics unavailable for aggregate-only days.
- Prove recovery on a production clone and credential-free isolated CI before
  any production deployment or data import. The verification environment MUST
  NOT duplicate production services, credentials, or upstream integrations.

## Capabilities

### New Capabilities

- `legacy-report-aggregate-recovery`: verified import, storage, exact supported
  report semantics, limitations, and rollout controls for retired aggregates.

### Modified Capabilities

- `proxy-runtime-observability`: Reports exposes honest recovered-history
  coverage and UTC aggregate-only results.
- `database-migrations`: the archive schema and import remain forward-only,
  cross-dialect, idempotent, and independently verifiable.

## Impact

Affected areas include ORM/Alembic schema, snapshot recovery CLI, Reports
repository/service/schema, Reports frontend, and clone/staging verification.
Lifetime rollups and the production database are not modified until staging
evidence is accepted.
