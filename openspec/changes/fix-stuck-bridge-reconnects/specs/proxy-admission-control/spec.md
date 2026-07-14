## MODIFIED Requirements

### Requirement: Stuck HTTP bridge response-create gate sessions are retired
When a visible HTTP bridge request times out waiting for a per-session response-create gate, the proxy MUST retire the bridge session only if pending visible request age meets or exceeds the configured stuck-gate retirement threshold. The retirement MUST emit a structured low-cardinality log and a Prometheus counter without raw keys or prompt content. After a bridge request is sent upstream, the proxy MUST bound the wait for `response.created` independently from keepalives and the overall request budget. Expiry MUST emit a terminal `response_created_timeout`, fail affected pending work, and release the session gate before the platform ingress timeout.

#### Scenario: Old pending work blocks a visible gate waiter
- **WHEN** a visible HTTP bridge request receives `response_create_gate_timeout`
- **AND** at least one visible pending request on the same session is older than the configured stuck-gate retirement threshold
- **THEN** the proxy retires the bridge session so later requests can create a fresh session
- **AND** the waiter is rejected cleanly with `response_create_gate_timeout`

#### Scenario: Healthy active stream is not retired during a normal wait
- **WHEN** a visible HTTP bridge request times out waiting for the gate
- **AND** the session has no pending visible request older than the configured stuck-gate retirement threshold
- **THEN** the proxy rejects only the waiter
- **AND** the bridge session remains available for the existing in-flight request

#### Scenario: Upstream never creates a response
- **WHEN** a successfully sent bridge request remains in the pre-created state beyond the configured response-created timeout
- **THEN** the proxy emits a terminal `response_created_timeout` before the ingress cutoff
- **AND** affected pending work and the response-create gate are released

#### Scenario: Active generation exceeds the startup timeout
- **WHEN** upstream emits `response.created` before the configured startup timeout
- **AND** generation continues longer than that timeout
- **THEN** the response-created watchdog does not fail the active generation
