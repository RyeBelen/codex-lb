## 1. Migration Graph

- [x] 1.1 Import the immutable production migration lineage and verify revision `20260726_000000_repair_request_usage_rollups_after_merge` resolves.
- [x] 1.2 Add the forward-only merge revision and verify Alembic reports exactly one head.

## 2. Schema Reconciliation

- [x] 2.1 Reconcile production-owned ORM tables and columns and verify model imports succeed.
- [x] 2.2 Reconcile the request-log account lookup index and verify migration policy plus schema drift checks pass.

## 3. Regression Verification

- [x] 3.1 Update verbose-capture migration expectations for the merged head and verify the focused regression test passes.
- [x] 3.2 Upgrade a disposable database from the exact production revision to head and verify `migration_policy=ok` and `schema_drift=none`.
- [x] 3.3 Run Ruff, backend migration/verbose-capture tests, frontend feature tests, the production frontend build, Compose validation, and strict OpenSpec validation.
