# Verification

Verified locally on Windows on 2026-09-14. The implementation covers all four corrected requirements and their scenarios. Repository scope, proxy selection/submission, Realtime creation/attachment/frames, background senders, and editor wording agree with the account-reservation design. No schema migration or stored selection rewrite is required.

## Local results

- 523 distinct backend tests passed across 18 files. The first broad run passed 293 and exposed 11 stale Realtime unit fixtures missing `enforced_model`. The fixtures now supply that field and isolate authorization database calls while asserting unknown-model filtering remains enabled. The subsequent 307-test run passed, including all affected unit tests and repeated routing/session integrations. The two runs cover 523 distinct tests.
- Coverage includes the five HTTP inference paths, key/account intersections, no-key and enforced-model routing, retry/revocation settlement, health preservation, sticky connections, multiple reservations, empty rules, new accounts, removal, deletion, unknown-model Realtime creation/frames/reattachment, model-less file ownership, background inference, external model sources, migrations, and quota/automation lifecycle.
- 442 frontend tests passed across 49 files covering model routing, accounts, API keys, and settings. The editor explicitly explains both routing directions and empty reservations.
- Frontend production build and ESLint passed. Backend Ruff and application type checks passed. Diff whitespace checks passed.
- Scoped OpenSpec change and main model-account-routing spec passed strict validation. Repository-wide validation reports 51 passing and the same nine pre-existing failures: compatibility-tooling, database-backends, frontend-architecture, model-catalog-compat, query-caching, responses-api-compat, upstream-proxy-routing, usage-error-metrics, usage-refresh-policy.
- The aggregate pre-commit local-ci hook was attempted but could not run because Windows has no `make`. This is scoped regression evidence, not a full repository CI pass. PostgreSQL was not exercised. One first-run SQLite worker teardown warning did not recur in the repeated session tests.

## Production preflight

Both public readiness URLs returned HTTP 200. The existing release is `be694c18c26f1920682ef937f652d7b8515cb47d`. Production contains 43 accounts, 33 API keys, one API-key account assignment, nine account/API-key grants, and one Astra rule with three selected accounts. Existing permission fingerprint is `2ad5572c8f9064dba30b98d2736cd3faa62f68599dfbc9d68bf4c37652b8e124`; model grant fingerprint is `cf31f8be4fd36055929b8beb0eec8de50391d97b70a0cc01e2752e2d1856b86b`.

Deployment verification is pending. Use the existing GitHub prod integration and compare code, saved selections, permissions, readiness, and real inference. Reuse the verified same-day snapshot backup; no new database migration is involved. Docker Desktop remained stopped.
