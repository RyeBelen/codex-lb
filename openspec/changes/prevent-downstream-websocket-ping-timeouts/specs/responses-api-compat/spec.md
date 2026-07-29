## ADDED Requirements

### Requirement: Client-facing WebSocket liveness does not interrupt active turns

The server MUST keep protocol pings enabled on client-facing Responses
WebSockets by default, and MUST NOT impose a pong acknowledgement deadline by
default. A delayed or absent pong MUST NOT by itself close an active Responses
turn with WebSocket code `1011`. The existing application-level downstream idle
timeout and pending-request budgets MUST remain authoritative for bounded
cleanup.

The ping interval and pong timeout MUST be configurable through canonical CLI
flags and environment variables. The pong timeout configuration MUST support an
explicit disabled value, and invalid or non-positive enabled values MUST fail
startup with a clear error.

#### Scenario: Active turn survives a missed pong deadline

- **GIVEN** a client-facing Responses WebSocket has a pending request
- **AND** the client does not acknowledge a protocol ping within the server library's historical default deadline
- **WHEN** the default client-facing WebSocket liveness policy is active
- **THEN** the server does not close the connection solely because the pong is missing
- **AND** the request remains governed by the configured stream and total request budgets

#### Scenario: Idle downstream session remains bounded

- **GIVEN** a client-facing Responses WebSocket has no pending requests
- **AND** no client application traffic arrives before the configured downstream idle timeout
- **WHEN** the idle timeout elapses
- **THEN** the application closes the downstream WebSocket
- **AND** releases its associated upstream session and admission resources

#### Scenario: Operator overrides ping liveness settings

- **WHEN** an operator configures the client-facing WebSocket ping interval or pong timeout through its canonical CLI flag or environment variable
- **THEN** the server uses the configured value
- **AND** the CLI flag takes precedence over the corresponding environment variable

#### Scenario: Invalid enabled ping setting fails startup

- **WHEN** an operator supplies a non-numeric or non-positive enabled ping interval or pong timeout
- **THEN** server startup fails with a clear configuration error
