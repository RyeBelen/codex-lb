## 1. Persistence and backend contracts

- [x] 1.1 Add the API-key verbose budget, verbose-capture model, migration, indexes, and cascade relationships; verify Alembic has a single head and migration upgrade/model tests pass.
- [x] 1.2 Add typed admin arm/disable API contracts and service/repository behavior, including validation, cache invalidation, and payload-free audit events; verify API-key unit and integration tests pass.

## 2. Proxy capture and request-log access

- [x] 2.1 Implement eligible JSON body bounding plus atomic slot claim/capture in proxy authentication; verify normal, oversized, ineligible, duplicate, and concurrent capture tests pass.
- [x] 2.2 Correlate captures with normal request logs, expose a list presence flag and admin-only detail endpoint, and integrate cleanup with request-log retention; verify request-log, authorization, and retention tests pass.

## 3. Dashboard experience

- [x] 3.1 Add frontend schemas, API calls, mutation state, and API-key detail controls with a default count of 10 and configurable 1-100 range; verify API-key component and flow tests pass.
- [x] 3.2 Add lazy captured-input loading and rendering to Request Details with truncation messaging and guest-safe behavior; verify request-log schema and detail-dialog tests pass.
- [x] 3.3 Update frontend mocks and screenshot fixtures for the new fields/endpoints; verify mock handler coverage and TypeScript checks pass.

## 4. Validation

- [x] 4.1 Run focused backend and frontend suites plus Ruff, type checks, build, migration checks, and `openspec validate --specs`; fix any regressions.
- [x] 4.2 Verify the implementation against every scenario in the change spec and record any intentional limitations before handoff.
