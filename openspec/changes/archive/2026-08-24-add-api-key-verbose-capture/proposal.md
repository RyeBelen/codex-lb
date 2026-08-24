## Why

Operators can see token and latency metadata for an API key, but they cannot inspect the actual inputs responsible for unexpected usage. Always-on payload logging is too broad and sensitive; a short, explicitly armed capture window provides focused diagnostics with a bounded storage and privacy impact.

## What Changes

- Add an admin control that arms an API key to capture the next configurable number of authenticated proxy request inputs, or disables an active capture.
- Consume capture slots atomically so concurrent requests cannot exceed the configured budget, and disable capture automatically when the budget reaches zero.
- Persist bounded request input snapshots with normal request-log records and expose whether a snapshot was truncated.
- Show remaining capture count on API-key details and captured input in the request-log details dialog.
- Audit capture enable/disable actions without including captured input in the audit event.

## Capabilities

### New Capabilities

- `api-key-verbose-capture`: Bounded, per-API-key request-input capture, dashboard controls, concurrency behavior, payload limits, and request-log presentation.

### Modified Capabilities

None.

## Impact

- Database schema: API-key capture budget and optional captured payload fields on request logs.
- Backend: API-key dashboard API, proxy authentication/capture path, request-log persistence and response schema, audit events, and migrations.
- Frontend: API-key detail controls, API contracts, request-log details, and associated tests/mocks.
- Security/privacy: request content is persisted only while explicitly armed and is size bounded; authorization headers and uploaded binary bodies are not captured.
