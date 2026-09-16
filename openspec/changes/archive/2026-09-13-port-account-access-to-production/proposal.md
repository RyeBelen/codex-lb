## Why

Production has newer model policy, request ownership, and Realtime support than the original account-access implementation. Port the feature onto the deployed branch without discarding those changes, and verify a recoverable rollout before replacing the serving process.

## What Changes

- Apply account allowlists to the current production request paths and migration graph.
- Enforce committed grants when attaching and sending on Realtime sideband connections.
- Verify the exact candidate and a schema-compatible rollback before deployment.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `account-api-key-access`: Cover Realtime attachment and frames, and safe migration rollout.

## Impact

Proxy selection and submission, Realtime relay, account management, dashboard, and an additive database migration. Existing accounts remain shared. The single production process requires independent recovery during a bounded restart.
