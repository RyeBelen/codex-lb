## Context

The live SQLite database contains a hardened `request_log_daily_aggregates`
table and fork-only Alembic head. Upstream has account/API-key lifetime rollups
and a safer leader-gated retention job.

## Decision

Map the fork head to the last shared revision, let normal upstream migrations
create empty rollups at an epoch watermark, then import only already-pruned
daily sums. Validate the hardened columns and aggregate parity before dropping
the retired table. Fresh upstream databases skip the import.

## Failure modes and rollback

Missing columns, a non-epoch watermark, or total mismatch aborts the migration
without dropping legacy data. Production cutover retains online SQLite backups;
rollback restores database and application together.

## Verification

Rehearse against the checksummed production snapshot, require one head, no
schema drift, `PRAGMA quick_check=ok`, and populated upstream rollups.

