# Local verification

Implementation was isolated on `codex/account-access-controls`, based on `513cc6ad`. The original checkout and its unrelated migration work were preserved. No push, deployment, live database migration, real upstream inference, or reset-credit consumption was performed.

## Requirement coverage

| Requirement | Implementation and verification |
| --- | --- |
| Account access policy | Independent account flag and normalized grants; route tests cover key-scope intersection, new and absent keys, explicit empty grants, regeneration, and deletion. |
| Dashboard access management | Authenticated GET/PUT endpoints, writer check, atomic validation, and account editor. API tests cover malformed and unknown IDs, missing accounts, unauthenticated access, and read-only viewers. Six editor tests cover save/reload, empty grants, shared mode, save failure, read-only controls, and load failure. |
| Routing and connection enforcement | Selection and upstream-send checks cover Responses, Chat Completions, compact, files, transcription, warm-up, HTTP bridge, and WebSocket traffic. Route tests cover failover, revoked file ownership, single-account routing, retry revocation, account health, and reservation settlement. Four session tests cover both canonical and compatible paths. |
| Account-backed client reads | Account-pool and aggregate upstream usage, reset-credit listing/redemption, and warm-up targets apply effective scope. Integration tests verify hidden capacity, hidden credits, and denied account targets. Existing administration and maintenance paths retain their authority. |
| Compatible migration | Fresh SQLite and PostgreSQL upgrade/check report the new revision, a valid migration graph, and no drift. Populated downgrade/upgrade tests preserve accounts and key assignments on both databases. Grant deletion cascades are verified through the API. |

The five requirements and their nine scenarios have implementation and test coverage. The independent grant relationship matches the design and does not reinterpret existing key assignments.

## Checks

Raw logs and JUnit XML remain local under `output/account-access-validation/` and are not committed. Runs overlap and should not be added together.

- The final full unit suite reported 3,777 passed, four failed, and 60 skipped. Its four failures are identical to the unchanged baseline. The 700-test proxy unit suite also passed independently.
- Broad account and API-key API coverage passed 105 tests.
- The final broad affected integration selection passed 227 tests with one mocked reset-credit session failure. After adding the access repository to that stub, the full reset-credit suite, both migration tests, and schema tests passed together, 29 tests total. All WebSocket, bridge, account-access, usage, and warm-up tests in the broad selection passed.
- PostgreSQL account policy and session coverage passed 23 tests with a migration-test setup failure. The test now uses the application's Alembic version-table sizing before stamping. Both migration tests passed on rerun. This corrected the test setup, not the production migration.
- The full frontend suite passed 858 of 859 tests. An unrelated API-key flow exceeded its existing 15-second timeout during the concurrent local run. All four tests in that file passed on isolated rerun. The six account-access editor tests also passed after the final test type correction.
- Frontend production build, TypeScript compilation, frontend lint, application Ruff, application type checking, and proxy architecture checks passed.
- A headless Chromium check used a local server, disposable data, and dummy credentials. It saved a restricted policy, reloaded it, verified the stored grant through the API, and checked the editor at desktop and 390-pixel widths. The screenshot is `output/account-access-validation/dashboard-access.png`.
- Strict validation passed for this OpenSpec change and the new main capability. Repository-wide strict validation reported 24 passing capabilities and 21 failures. The unchanged baseline reported 23 passing capabilities and the identical 21 failures.

## Baseline failures and limits

The unchanged baseline at `513cc6ad` was tested separately in a detached worktree with the same dependency environment.

- Its full unit suite reported 3,770 passed, four failed, and 60 skipped. Two failures are API-key cache fakes missing `allow_gpt6_astra`; two are legacy migration remap tests adding that column twice.
- Its complete SQLite integration migration suite reported ten passed, seven failed, and three skipped. All seven failures match the existing Astra-column duplicate failures in the feature worktree.
- Full repository type checking reported the same five diagnostics in both worktrees: two in a tracked diagnostic script, one API-key repository fake signature, and two Windows `os.fork` references. Application-only type checking passed.
- The identical 21 existing OpenSpec failures remain outside this feature. No existing spec was rewritten to silence them.
- Skips include unavailable Helm and POSIX-only checks on Windows. PostgreSQL tests used a disposable PostgreSQL 18 container. Test logs also contain mock-coroutine and SQLite teardown warnings.
- Early runs exposed unrealistic WebSocket response fixtures that delivered responses before requests were sent, plus isolated unit tests without a database. Their fixtures now model request ordering and the policy repository explicitly. The new database-backed access and session tests use real policy enforcement.

Feature verification is complete with the repository-level failures above documented as warnings. Deployment remains on hold because the full repository gates are not green. The feature has not been pushed or deployed.
