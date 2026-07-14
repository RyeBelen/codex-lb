## Verification evidence

### Production-clone recovery

- Pre-prune snapshot SHA-256: `f6f0d2d3a508f9dab3a8ab6556d031fc12e0bbafc948394aa8c2995367089d61`.
- Current-clone raw rows before recovery: 45,023.
- Verified missing candidates: 54,551 ids (`23700..78250`), June 12 through July 6, with zero absent-account references.
- Candidate-id SHA-256: `f0be7e70ce6f38a02888df09cda6437cd4ba083922711d6a063674cb27b079d3`.
- First backfill inserted 54,551 facts; the second dry run found zero candidates.
- Raw-row, account-rollup, API-key-rollup, and fold-watermark checksums/state were unchanged.
- Source snapshot rows: 97,591; compact-fact plus raw rows: 97,591; both EXCEPT directions returned zero.
- SQLite `quick_check` returned `ok`; foreign-key violations were zero.

### Seven-day clone prune

- A migrated pre-prune clone projected and deleted 54,756 rows older than the rolling seven-day cutoff, leaving 42,835 raw rows.
- The second prune removed zero rows.
- Compact-fact plus raw history remained an exact 97,591-row match to the source snapshot in both EXCEPT directions.
- Lifetime account/API-key rollup checksums were unchanged; `quick_check` returned `ok`; foreign-key violations were zero.

### Automated verification

- Strict OpenSpec validation passed.
- Ruff and scoped type checks passed for changed modules; the environment-wide type command has an unrelated missing optional `prometheus_client` dependency.
- Focused aggregate/history suites: 86 passed.
- The full suite has an existing `main` collection failure: `tests/unit/test_load_balancer.py` imports removed `_filter_states_for_sticky_account_caps`.
- The Railway Docker build completed its frontend `bun run build` successfully.

### Isolated Railway staging

- Environment: `hist-analytics-stage`; feature commit: `6391e616041073e8317e3e1e08b304807f5ef7f7`.
- Deployment: `b7504097-3d8c-4937-afb9-740256ebb01f`; migration head: `20260714_020000_add_request_log_historical_facts`.
- Staging used its own empty environment volume instance and a disposable control database; production storage was never mounted or mutated.
- With 12 deterministic requests, a seven-day prune moved exactly 8 old rows to compact history and retained 4 raw rows.
- Before/after dashboard and report totals were identical: 12 requests, 2 errors, 1,266 input tokens, 306 output tokens, 120 cached tokens, and $0.78 cost.
- The second prune removed zero rows; retention configuration reported 7; the redeployed service returned HTTP 200 from `/health/live`.
- The staging deployment was removed after verification, leaving no running replicas.

## Production rollout and rollback

1. Take a fresh online SQLite backup and record its SHA-256 immediately before rollout.
2. Merge the verified feature branch and let Railway deploy the matching commit with retention initially unchanged.
3. Run the guarded backfill dry run against the immutable pre-prune snapshot and require the recorded 54,551 count and candidate-id checksum.
4. Apply the backfill, require an immediate zero-candidate rerun, then verify reports and database integrity before changing retention.
5. Set request-log retention to seven days only after the recovery checks pass.
6. If migration or backfill validation fails, stop the deployment and restore the matching code plus pre-rollout database backup; do not perform a code-only rollback after data migration.
