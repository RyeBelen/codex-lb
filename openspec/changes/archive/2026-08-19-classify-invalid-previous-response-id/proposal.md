## Why

The Codex upstream now sometimes rejects a stale Responses WebSocket anchor as `invalid_request_error` with only the message `Invalid \`previous_response_id\`.`. codex-lb does not classify that shape as continuity loss, so it leaks a raw HTTP-style 400 instead of using its existing recovery path.

## What Changes

- Classify the observed no-code, no-param invalid `previous_response_id` envelope as a stale previous-response error.
- Reuse the existing fresh-context replay and sanitized continuity-failure behavior.
- Add regression coverage at the Codex-native WebSocket surface.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: Recognize the observed noncanonical stale-anchor error envelope and apply the existing recovery contract.

## Impact

- Shared Responses error classification in `app/core/errors.py`.
- Codex-native Responses WebSocket behavior and its integration coverage.
- No API additions, configuration, migrations, or dependencies.
