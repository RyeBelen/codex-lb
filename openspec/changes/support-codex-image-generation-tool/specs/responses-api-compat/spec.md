## ADDED Requirements

### Requirement: Backend Codex Responses accepts image_generation tools
When handling backend Codex Responses traffic on `/backend-api/codex/responses`, the service MUST accept tool definitions with type `image_generation` and forward them upstream unchanged. This backend-only allowance MUST apply to direct HTTP requests, websocket `response.create` requests, and internal bridge owner-handoff revalidation for forwarded backend requests. `/v1/responses` MUST continue rejecting `image_generation` with an OpenAI `invalid_request_error`.

#### Scenario: backend HTTP request includes image_generation
- **WHEN** a client sends `POST /backend-api/codex/responses` with `tools=[{"type":"image_generation"}]`
- **THEN** the service accepts the request instead of returning a local validation error
- **AND** the forwarded upstream Responses payload still includes `{"type":"image_generation"}`

#### Scenario: backend websocket request includes image_generation
- **WHEN** a client sends a websocket `response.create` event on `/backend-api/codex/responses` with `tools=[{"type":"image_generation"}]`
- **THEN** the service accepts the event instead of returning a local validation error
- **AND** the forwarded upstream `response.create` payload still includes `{"type":"image_generation"}`

#### Scenario: backend bridge owner handoff preserves image_generation allowance
- **WHEN** an internal `/internal/bridge/responses` forward revalidates a backend Codex Responses payload that includes `tools=[{"type":"image_generation"}]`
- **THEN** the owner instance accepts the forwarded payload instead of failing local tool validation

#### Scenario: v1 responses remains strict
- **WHEN** a client sends `POST /v1/responses` with `tools=[{"type":"image_generation"}]`
- **THEN** the service returns a 4xx OpenAI `invalid_request_error`
