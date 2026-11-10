## ADDED Requirements

### Requirement: Native stream queues schedule ready consumers fairly

The native helper reader and WebSocket message pump MUST allow ready consumers to run during buffered bursts. A continuously ready consumer MUST receive HTTP chunks and WebSocket text and binary frames in order, followed by their terminal event, when a burst exceeds the per-stream queue capacity. Queues MUST remain bounded. A stalled consumer MUST fail only its owned stream without blocking or cancelling other streams sharing the helper. Closing or cancelling a stream MUST release its adapter ownership and allow client shutdown to complete within the existing cancellation bounds.

#### Scenario: Buffered HTTP burst reaches its terminal

- **WHEN** the helper emits more chunks than the event queue capacity while the HTTP consumer continuously reads
- **THEN** the consumer receives every chunk in order and reaches end of stream without consumer backpressure failure

#### Scenario: Buffered WebSocket burst reaches its terminal

- **WHEN** the helper emits more text and binary frames than either queue capacity while the relay continuously receives
- **THEN** every frame reaches the relay in order before the close event

#### Scenario: Stalled stream does not stop another stream

- **WHEN** one consumer stops reading and overflows its bounded queue while another stream is active
- **THEN** the stalled stream fails with consumer backpressure and the other stream completes without replay or cancellation

#### Scenario: Consumer cancels during a burst

- **WHEN** a consumer closes or is cancelled during a native burst
- **THEN** only that stream's ownership is released and helper shutdown completes within its cancellation bounds

### Requirement: Local native backpressure does not penalize accounts

Native consumer-backpressure failures MUST use the existing account-neutral process transport failure classification in both HTTP and WebSocket paths. They MUST NOT introduce account cooldowns, cross-account continuation, or replay eligibility after dispatch. Native WebSocket failures MUST record their operation and failure phase in internal diagnostics without logging request payloads or credentials.

#### Scenario: Local overflow reaches the WebSocket relay

- **WHEN** the native WebSocket adapter reports consumer backpressure
- **THEN** the relay receives the account-neutral process transport error code and internal logs identify the operation and failure phase

#### Scenario: Local overflow reaches the HTTP transport

- **WHEN** direct or routed native HTTP streaming reports consumer backpressure after dispatch
- **THEN** its terminal uses the account-neutral process transport error code and remains non-replayable
