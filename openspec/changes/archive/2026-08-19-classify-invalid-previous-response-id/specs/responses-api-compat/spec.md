## ADDED Requirements

### Requirement: Invalid previous-response shorthand uses stale-anchor recovery

Responses WebSocket handling MUST classify an upstream `invalid_request_error` whose message is exactly `Invalid \`previous_response_id\`.` as previous-response continuity loss when the envelope omits both `code` and `param`. It MUST apply the same replay or sanitized continuity-failure behavior used for canonical `previous_response_not_found` errors instead of forwarding the raw 400 error.

#### Scenario: Codex-native stale anchor uses shorthand error envelope

- **WHEN** a Codex-native Responses WebSocket follow-up carries `previous_response_id`
- **AND** upstream returns `type=invalid_request_error` with message `Invalid \`previous_response_id\`.` and no `code` or `param`
- **THEN** codex-lb applies its existing stale-anchor recovery behavior
- **AND** the client does not receive the raw upstream 400 error

#### Scenario: Unrelated invalid requests remain unchanged

- **WHEN** upstream returns an `invalid_request_error` whose message does not exactly identify an invalid `previous_response_id`
- **THEN** codex-lb does not classify it as previous-response continuity loss solely because `code` and `param` are absent
