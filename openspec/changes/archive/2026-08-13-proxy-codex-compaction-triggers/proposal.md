## Why

Codex remote compaction v2 sends a terminal `compaction_trigger` through the normal Responses endpoint. The proxy currently rewrites that request to the standalone `/codex/responses/compact` endpoint, which now returns 404 and prevents long-running Codex sessions from compacting.

## What Changes

- Forward valid terminal `compaction_trigger` requests unchanged through the normal Codex Responses streaming path.
- Preserve subscription-account routing and reject duplicated or non-terminal triggers before upstream dispatch.
- Pass the upstream compaction SSE lifecycle through instead of synthesizing it from a standalone compact response.
- Leave `/backend-api/codex/responses/compact` and `/v1/responses/compact` unchanged for explicit standalone callers.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: Replace the legacy trigger-to-standalone-compact bridge with transparent Responses proxying.

## Impact

- `app/modules/proxy/api.py`
- Codex Responses integration tests
- `openspec/specs/responses-api-compat/spec.md`
- No new dependency, setting, API route, or database migration
