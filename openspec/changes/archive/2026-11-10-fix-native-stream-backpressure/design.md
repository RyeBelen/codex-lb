## Context

The deployed adapter multiplexes helper events through a 64-item queue per stream and WebSocket frames through another 64-item queue. Buffered pipe reads and queue operations need not suspend. Producers can therefore fill a queue before its ready consumer runs. A 256-event loopback probe reproduces both HTTP and WebSocket loss. Compaction timing is observed by the user, but the exact original upstream exception was not retained.

## Goals / Non-Goals

Deliver buffered bursts to ready consumers in order, keep memory bounded, isolate stalled streams, and prevent local overflow from penalizing an account. Preserve safe diagnostic phase information. Do not alter continuity ownership, replay eligibility, database schema, or upstream compaction payloads.

## Decisions

- Yield cooperatively after successful helper-event and WebSocket-message enqueues. When a queue is full, allow at most 64 cooperative scheduling turns before reporting overflow. Full HTTP parsers use several ready-task transitions per chunk, so one turn per event alone still loses bursts in the wire probe. The grace is bounded by scheduling turns, never waits for consumer I/O, and does not increase queue capacity. Keep the existing overflow cancellation for genuinely stalled consumers. Waiting indefinitely for queue capacity would block every stream; raising limits would only move the failure threshold.
- Centralize the native transport error's account-neutral classification, adding consumer backpressure to the existing helper-local phases. Use the existing process transport error code so relay health logic retains its account-neutral path. Do not make ambiguous dispatched requests replayable.
- Log native WebSocket operation and phase internally without payloads or credentials. Keep the public error envelope unchanged.
- Test through the real subprocess adapter and upstream relay, including native wire tests in a Linux candidate container. The HTTP and WebSocket terminal must follow every accepted burst event in order.

## Risks / Trade-offs

Cooperative scheduling adds a scheduling point per event. Verify throughput with large bursts and concurrent streams. Consumers that remain slower than producers still fail at the bounded limit; this change does not promise unlimited buffering. Cancellation must leave no owned streams or pending commands behind. Existing owner-pinned requests remain fail-closed for truly unavailable accounts.

## Migration Plan

No schema migration. Build a derived immutable image from the exact deployed image with only the reviewed Python patch. Run isolated staging regressions and inference probes. Preserve the previous image, application configuration, encryption configuration, and a consistent SQLite backup. Verify an independent watchdog can monitor readiness and restore the previous deployment without model inference, then perform a supervised rollout and observe production health and inference. Do not stop the only serving instance without a tested recovery mechanism.
