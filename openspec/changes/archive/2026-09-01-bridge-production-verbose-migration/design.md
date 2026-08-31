## Context

See [proposal.md](proposal.md) for motivation. The deployed SQLite volume is owned by the production migration lineage, while fork `main` contains a parallel fork lineage and the verbose-capture child. Startup is configured to fail closed on unknown revisions and schema drift.

## Goals / Non-Goals

**Goals:**

- Preserve the deployed revision and data while making it a known ancestor of the new head.
- Apply verbose capture through Alembic and retain a single-head graph.
- Keep ORM metadata and manual index requirements consistent with the combined schema.

**Non-Goals:**

- Downgrading, manually stamping, or directly editing the production database.
- Importing unrelated proxy, dashboard, or reporting behavior from the production source branch.
- Replacing the existing named volume or migrating application data.

## Decisions

### Import the immutable production lineage and join it forward

Copy the existing production revision files unchanged, retain the existing verbose-capture lineage unchanged, and add a new merge revision with both heads as parents. This preserves historical revision identity and lets Alembic traverse whichever branch a database currently occupies. Reparenting the already-merged verbose revision or stamping the live database was rejected because either would rewrite migration history or bypass schema work.

### Reconcile schema metadata at the merge boundary

Add the production-owned tables and columns to ORM metadata and recreate the request-log account lookup index at the merge revision when the production optimization revision previously removed it. This makes the combined physical schema match both ORM drift detection and the repository's required-index policy. Ignoring drift was rejected because startup is intentionally fail-closed.

### Validate from the deployed revision

Build a disposable database to the exact deployed revision, then upgrade it to head and run migration policy plus schema drift checks. Fresh-only migration tests were rejected because they would not exercise the branch convergence path used in production.

## Risks / Trade-offs

- **Imported production tables are not yet used by all fork services** → Keep them represented in ORM metadata so they remain stable and non-destructive.
- **Parallel branches can disagree about indexes** → Reconcile the required index idempotently in the forward merge revision and cover it with drift checks.
- **A failed production upgrade could restart-loop the new container** → Keep the existing routed container untouched until the replacement reaches readiness and exact feature checks pass.

## Migration Plan

1. Verify the disposable production-revision-to-head upgrade and drift checks.
2. Build and deploy the new image against the existing named volume.
3. Require container readiness and confirm the merged Alembic head.
4. Route traffic only after backend routes and frontend feature labels are present.
5. If startup fails, stop the unrouted replacement and leave the existing routed container and database untouched; do not downgrade or stamp the database.
