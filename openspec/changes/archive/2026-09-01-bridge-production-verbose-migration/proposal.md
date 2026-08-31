## Why

The Dokploy production database is stamped at the production-line revision `20260726_000000_repair_request_usage_rollups_after_merge`, while fork `main` previously contained only its parallel migration lineage and the verbose-capture revision. A build from `main` therefore fails closed before startup because it cannot resolve the live revision.

## What Changes

- Import the existing production migration lineage without rewriting any merged revision.
- Add a forward-only merge revision joining the production lineage and verbose-capture lineage into one Alembic head.
- Reconcile ORM metadata and the request-log account lookup index so post-upgrade drift checks remain clean.
- Verify upgrades both from the production revision and from a fresh database.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `database-migrations`: Require the migration graph to recognize the deployed production revision, converge with verbose capture at one head, and pass post-upgrade schema drift checks.

## Impact

- Affects Alembic revisions, database ORM metadata, migration verification tests, and Dokploy startup migration compatibility.
- Does not downgrade, stamp, or manually mutate the production database outside Alembic.
