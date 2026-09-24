## 1. Account-oriented backend contract

- [x] 1.1 Add typed account allowed-model schemas and resolved-catalog mapping in the model-routing service.
- [x] 1.2 Add atomic repository replacement for one account using the existing policy/grant tables and no migration.
- [x] 1.3 Add authenticated account allowed-model GET/PUT routes with catalog, model, account, conflict, and read-only validation.
- [x] 1.4 Add backend integration coverage for retrieval, atomic replacement, clearing, stale selections, unavailable catalogs, invalid models, and authorization.

## 2. Account dashboard editor

- [x] 2.1 Add frontend account API/schema contracts and mock handlers for allowed models.
- [x] 2.2 Add the Allowed models checkbox card to account detail with empty-as-all, stale-selection, error, busy, and read-only states.
- [x] 2.3 Remove the global Settings editor and its dead frontend API/component/tests while retaining the backend compatibility API.
- [x] 2.4 Add focused frontend component and integration coverage.

## 3. Documentation and verification

- [x] 3.1 Sync the stable model-account-routing spec and context to the per-account workflow.
- [x] 3.2 Run strict OpenSpec validation, focused backend/frontend tests, frontend typecheck/lint, Python lint/format checks, and final diff/dead-reference review.
