## MODIFIED Requirements

### Requirement: Stuck HTTP bridge response-create gate sessions are retired

The proxy MUST retain the existing waiter-triggered retirement behavior for stale HTTP bridge response-create gate owners. The proxy MUST also enforce an owner-side deadline when the upstream stream does not produce `response.created`. This rule applies to an eventless stream and to a stream with matched `response.*` activity before `response.created`. The owner-side deadline MUST start from a monotonic timestamp recorded immediately before the current upstream send. The deadline MUST use the smaller of the configured stuck-gate retirement threshold and 240 seconds. The deadline MUST run without a second gate waiter. The deadline MUST remain active when periodic SSE keepalives are disabled.

The owner-side watchdog MUST apply only while the request owns the response-create gate and awaits `response.created`. The request MUST have no response id, recorded `response.created` latency, downstream-visible output, or sequence evidence. Non-response telemetry such as `codex.rate_limits` MUST NOT disable or reset the watchdog. Before matched `response.*` activity, the deadline MUST remain anchored to the current upstream send. Matched `response.*` activity MUST keep the watchdog active and reset its deadline from the latest upstream response activity. A response-created milestone or downstream-visible evidence MUST disable this narrow watchdog. Existing timeout behavior then remains unchanged.

When the owner-side deadline expires, the proxy MUST recheck eligibility, emit a structured low-cardinality log and the existing stuck-retirement Prometheus counter, terminally fail and settle every pending request exactly once, and retire the whole bridge session. It MUST NOT transparently replay the timed-out request, move it to another account, or write an account-health failure for the missing-created timeout.

#### Scenario: Lone eventless gate owner is retired before the client timeout

- **GIVEN** a visible HTTP bridge request owns the response-create gate
- **AND** its current `response.create` send produced no matched `response.*` event, response id, or downstream-visible output
- **AND** no second request waits for the gate
- **WHEN** the smaller of the configured stuck threshold and 240 seconds elapses after the current send
- **THEN** the proxy emits an explicit terminal failure and retires the bridge session
- **AND** recovery occurs before the native client's 300-second parsed-event idle timeout

#### Scenario: Send time rather than request age anchors the deadline

- **GIVEN** a request spends most of its budget waiting for admission before it sends `response.create`
- **WHEN** the upstream send succeeds
- **THEN** the owner-side deadline begins from that current send
- **AND** earlier queue or admission time does not make the request immediately stale

#### Scenario: Leading telemetry does not mask an eventless owner

- **GIVEN** a pre-created gate owner receives `codex.rate_limits` but no matched `response.*` lifecycle event
- **WHEN** the owner-side deadline elapses
- **THEN** the telemetry does not refresh or suppress the deadline
- **AND** the proxy fails and retires the session

#### Scenario: Response lifecycle evidence resets the missing-created watchdog

- **GIVEN** a pre-created request receives matched `response.*` activity
- **AND** the request has no response id, recorded `response.created` latency, or downstream-visible output
- **WHEN** a new response-lifecycle event arrives
- **THEN** the watchdog deadline resets from the latest upstream response activity
- **AND** the watchdog remains active until response-created or downstream-visible evidence appears

#### Scenario: Response-created or visible evidence disables the narrow watchdog

- **GIVEN** a pre-created request receives a response id, recorded `response.created` latency, or downstream-visible output
- **WHEN** the missing-created deadline would otherwise elapse
- **THEN** this watchdog does not retire the session
- **AND** existing stream, request-budget, and waiter-triggered timeout behavior remains authoritative

#### Scenario: Timeout is fail-closed and account-neutral

- **GIVEN** an eventless pre-created owner reaches the owner-side deadline
- **WHEN** terminal cleanup runs
- **THEN** every pending request is settled exactly once and the whole session is retired
- **AND** the proxy does not replay the timed-out request or submit it on another account
- **AND** the selected account is not marked unhealthy solely because `response.created` was missing
