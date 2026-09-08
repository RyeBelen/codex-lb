## Verification

The permission is persisted and returned by the API key repository/service/schema path. Existing cache invalidation includes permission updates. Shared request policy checks the effective model before upstream work; both client catalog builders omit unauthorized Astra entries, including metadata and source catalogs. Dashboard selection uses its separate administrator catalog.

All scenarios are implemented. HTTP regression tests cover Responses, compact, Chat Completions, enforced models, and the existing trailing-slash rejection. Tests also cover WebSocket denial, a successful enabled request using a stub upstream, key isolation, allowlist precedence, catalog changes after enable/revoke, omitted/null updates, creation, regeneration, and no-key denial. The migration test upgrades historical rows, checks schema drift, downgrades, and upgrades to a single head again.

Validation:

- 123 focused backend tests passed (API key service/repository, request policy, Astra routes and migration).
- The existing API key API and request policy suites separately passed all 104 tests.
- 27 create/edit dialog tests passed; frontend type checking and production build passed.
- Scoped Ruff and ESLint checks passed.
- All 44 main specs pass normal OpenSpec validation. The changed API key spec and change pass strict validation. Global strict validation reports pre-existing placeholder purpose text in 21 unrelated specs; no unrelated specs were edited.

No deployment or live upstream request was performed. Astra access still requires upstream model availability and eligible account capacity. Cache revocations use the existing propagation interval; already-running requests are not canceled.
