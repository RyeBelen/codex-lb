## 1. Port Weekly Quota Semantics

- [x] 1.1 Port fork commit `a2a1cd39` onto the current deployed lineage and resolve only compatibility conflicts.
- [x] 1.2 Ensure shared quota derivation blocks exhausted weekly windows without changing explicit unavailable states.
- [x] 1.3 Ensure proxy state construction applies secondary inference to weekly, not monthly, rows.

## 2. Regression Coverage

- [x] 2.1 Update unit coverage for weekly exhaustion with credit metadata and primary/secondary precedence.
- [x] 2.2 Update account and dashboard integration coverage so weekly-exhausted accounts are not reported active.
- [x] 2.3 Update routing, persistence, and sticky-session coverage so weekly-exhausted accounts are not selected.

## 3. Verification and Deployment

- [x] 3.1 Validate the OpenSpec change strictly and run focused Python tests, lint, and type checks.
- [x] 3.2 Run the broader local CI gate or document any environment-only failure with independent product-path verification.
- [x] 3.3 Push an exact fork-only deployment tag and deploy the compose service without changing the persistent volume.
- [x] 3.4 Verify readiness, migration integrity, logs, reconnect-loop protections, and that no active dashboard summary has zero weekly remaining.
