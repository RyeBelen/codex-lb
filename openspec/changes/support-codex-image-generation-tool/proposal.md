## Why

Recent Codex CLI builds include `image_generation` in the default tool inventory they send to `/backend-api/codex/responses`. `codex-lb` currently rejects that built-in tool in the shared Responses validator, so backend Codex requests fail locally with `invalid_request_error` before they ever reach the upstream service.

## What Changes

- Add a backend Codex Responses-specific tool validation path that accepts `image_generation` on `/backend-api/codex/responses`.
- Apply the same backend-only tool policy to HTTP requests, websocket `response.create` requests, and internal bridge revalidation so owner handoff does not reintroduce the same failure.
- Keep `/v1/responses` and `/v1/chat/completions` tool validation behavior unchanged.
- Add regression coverage for backend HTTP and websocket acceptance plus continued OpenAI-style rejection on `/v1/*`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: backend Codex Responses routes accept `image_generation` tool definitions while preserving the stricter `/v1` contract.

## Impact

- Affected code: `app/core/openai/requests.py`, `app/modules/proxy/request_policy.py`, `app/modules/proxy/api.py`, `app/modules/proxy/service.py`
- Affected tests: backend HTTP/websocket Responses compatibility coverage and tool validation regression tests
- External behavior: `/backend-api/codex/responses` becomes compatible with Codex CLI tool inventories that include `image_generation`; `/v1/*` and chat remain unchanged
