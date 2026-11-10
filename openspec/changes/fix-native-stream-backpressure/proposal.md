## Why

Buffered native HTTP and WebSocket bursts can overflow bounded queues before a ready consumer runs. The resulting local failure can penalize a healthy account and block owner-pinned continuations, including chats recovering from compaction.

## What Changes

- Schedule consumers fairly at both native queue producers without increasing queue limits or blocking the shared reader on a slow stream.
- Classify local consumer backpressure as an account-neutral transport failure and retain safe failure-phase diagnostics.
- Cover buffered bursts, terminal ordering, slow-consumer isolation, cancellation, and account-neutral relay behavior.
- Stage an immutable patch against the deployed image, verify an independent rollback mechanism, and preserve production data and routing during release.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `outbound-http-clients`: bounded native queue fairness and local-failure classification.

## Impact

Python native adapter, HTTP and WebSocket transport classification, regression tests, and deployment runbook. No database migrations, queue-limit settings, account switching, or upstream replay changes.
