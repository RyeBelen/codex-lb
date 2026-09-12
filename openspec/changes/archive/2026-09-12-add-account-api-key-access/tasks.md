## 1. Persistence and administration
- [x] 1.1 Add independent account grants and migration; verify SQLite and PostgreSQL migration tests and schema checks.
- [x] 1.2 Add atomic authenticated access read/write endpoints; verify validation, read-only access, deletion, and key-scope independence through API tests.
## 2. Enforcement and dashboard
- [x] 2.1 Apply account access to selection, failover, pinned owners, and reused transports; verify real route and session regression tests.
- [x] 2.2 Scope account-backed client operations; verify usage, reset-credit, and warm-up tests.
- [x] 2.3 Add the account access editor; verify save/reload, failure, read-only, and empty-grant frontend tests.
## 3. Verification and completion
- [x] 3.1 Run backend and frontend regression suites, lint, type checks, build, and strict OpenSpec validation; record results and baseline failures.
- [x] 3.2 Review the complete diff, sync stable context, verify and archive the change, and commit only this feature.
