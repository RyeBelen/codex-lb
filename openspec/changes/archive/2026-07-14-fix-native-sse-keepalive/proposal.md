## Why

Codex Desktop requests to the native `/backend-api/codex/responses` route can be misclassified as OpenAI SDK traffic when they use an OpenAI-shaped payload and `Accept: text/event-stream`. The proxy then emits comment-only keepalives that do not reset Codex's 300-second SSE idle watchdog, producing repeatable disconnects during upstream silence.

## What Changes

- Give allowlisted native Codex identity precedence over generic OpenAI SDK payload and `Accept` heuristics while preserving explicit SDK fingerprint precedence.
- Preserve the public OpenAI SDK contract while ensuring native Codex HTTP/SSE streams receive parseable `codex.keepalive` liveness events.
- Add focused classifier coverage using the real Codex Desktop request fingerprint and verify the existing stalled-stream keepalive contract tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: Require native Codex Responses requests to retain native SSE framing even when their payload also matches the OpenAI Responses shape.

## Impact

The change affects request classification and streaming behavior in `app/modules/proxy/api.py` plus focused integration tests. It does not change request or response schemas, account selection, upstream transport selection, or the public `/v1/responses` contract.
