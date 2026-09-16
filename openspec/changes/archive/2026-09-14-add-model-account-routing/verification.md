# Local verification

Verified on Windows on 2026-09-14 against `origin/prod` commit `0f4e9743f86226daa7555d94d674daf9e0afbb1c`. No deployment or production policy changes were performed. Docker remained stopped.

| Dimension | Result |
| --- | --- |
| Completeness | Storage, migration, dashboard API, editor, routing checks, and regression coverage implemented |
| Correctness | All four requirements and their scenarios covered by code and local checks |
| Coherence | Existing account-scope intersection and submission boundaries reused; direct background senders check model-only scope |

## Test results

- 225 backend regression tests passed across account API-key access, HTTP/WebSocket/Realtime access revocation, account-access migrations, warm-up, transcription, sticky routing, and external model-source routing.
- 200 backend tests passed across the four new model-routing test files, limit warm-up unit tests, automation unit/API tests, and quota-warm-up cancellation/claim tests.
- 16 existing and extended connection tests passed, including six new model-policy Realtime cases across three attachment URLs and text/binary frames. Ten cases overlap the 225-test run, for 431 distinct backend tests in total.
- 189 frontend tests passed across 20 files covering the model editor, settings, existing account-access editor, and mock endpoint coverage.
- Frontend production build and ESLint passed. Backend Ruff and `ty check app` passed. `git diff --check` passed.
- SQLite migration upgrade, schema-drift check, downgrade, and re-upgrade passed. Account deletion cascades grants while retaining the model policy. No production database was accessed. PostgreSQL was not exercised locally.

The new tests cover invalid payloads preserving prior policy, strict boolean validation, normalized and deduplicated values, dashboard authentication, read-only access, empty restrictions, account deletion and pending deletion, account/key scope intersection, enforced models, retries, no fallback, aliases in warm-up, transcription selection, reused connections, reservation settlement, account-health preservation, background sends, and individual/Pro shortcut selection in the editor.

The limit-warm-up unit fixture uses epoch arithmetic for synthetic dates before 1970, avoiding Windows' rejection of negative timestamps. Its model-policy database dependency is mocked only in unit tests; integration tests exercise committed policies through the real background sender boundaries.

## Specification validation

The scoped change validates with OpenSpec 1.3.0 in strict mode. The existing main specifications were unchanged when the repository-wide strict check returned 50 passing and nine failing specifications. The failures concern requirement text missing SHALL or MUST in:

- compatibility-tooling
- database-backends
- frontend-architecture
- model-catalog-compat
- query-caching
- responses-api-compat
- upstream-proxy-routing
- usage-error-metrics
- usage-refresh-policy

These are pre-existing specification errors outside this change. They are not represented as passing checks. After archive, the new main model-account-routing specification is also validated independently.

## Limits

This was a scoped local regression run, not the entire repository test suite. PostgreSQL, live production inference, and cloud merge/deployment gates were not run. Realtime filtering requires a known model, currently supplied by the API key's enforced model; opaque call bodies are not parsed to discover it. No critical implementation or scenario gaps were found within the documented scope.
