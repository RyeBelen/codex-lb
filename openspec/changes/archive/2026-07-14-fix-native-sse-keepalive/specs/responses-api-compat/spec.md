## ADDED Requirements

### Requirement: Native Codex Responses streams retain native liveness framing

When `POST /backend-api/codex/responses` carries an allowlisted native Codex originator or native Codex user-agent, the service MUST classify the request as native Codex traffic even if the payload matches the OpenAI Responses shape and the request accepts `text/event-stream`. Explicit OpenAI SDK fingerprints, including `x-stainless-*` headers or an OpenAI SDK user-agent, MUST remain authoritative when they conflict with native identity. While a native stream is waiting for an upstream event, the service MUST emit data-bearing `codex.keepalive` liveness events rather than comment-only keepalives so the Codex EventSource idle watchdog observes activity. Requests without native Codex identity MUST retain the existing OpenAI SDK contract classification behavior.

#### Scenario: Codex Desktop request also matches OpenAI SDK shape heuristics

- **WHEN** a Codex Desktop request posts an OpenAI-shaped streaming payload to `/backend-api/codex/responses` with `Accept: text/event-stream` and a recognized native Codex originator
- **AND** the upstream stream remains silent longer than the configured keepalive interval
- **THEN** the first downstream liveness frame is a data-bearing `codex.keepalive` event
- **AND** the stream is not limited to comment-only keepalives

#### Scenario: OpenAI SDK client has no native Codex signals

- **WHEN** an OpenAI SDK client posts a streaming payload to `/backend-api/codex/responses` without a recognized native Codex originator or transport header
- **THEN** the service preserves the existing OpenAI SDK Responses contract
- **AND** native `codex.*` events are not exposed to that client

#### Scenario: Explicit SDK fingerprint conflicts with native identity

- **WHEN** a request includes both an allowlisted native Codex identity and an explicit `x-stainless-*` SDK fingerprint
- **THEN** the service preserves the OpenAI SDK Responses contract
- **AND** native `codex.*` events are not exposed to that client
