## Context

The original feature commit predates production's model deny policy, model catalog routing, and request lifecycle changes. The production application serves the deployment agent's inference and has one replica with a persistent data volume.

## Goals / Non-Goals

Goals are to preserve current production behavior, enforce account access across all current client transports, and deploy with independent recovery. No account restriction is enabled as part of rollout. Provider credential maintenance retains its existing authority.

## Decisions

Port the feature onto the current production revision instead of deploying its older base. Keep account policy in the normalized grant repository and query it at selection and submission boundaries. Realtime sideband checks run before connection and each client text or binary frame. An access denial closes the relay and releases its lease without account health penalties.

Preserve current request ownership, prewarm accounting, model policies, and cancellation cleanup. The additive migration follows production's model-deny revision. Rollback uses the candidate migration tooling to remove only the added access schema before restarting the preserved image; a backup restore is reserved for a failed migration before new writes.

## Risks / Trade-offs

Database checks add latency. Test connection reuse and authorization delays. SQLite cannot have overlapping application replicas. Confirm the live engine, back up and integrity-check the database, stage the exact candidate, and establish an independent restart/rollback controller before cutover. Public readiness and authenticated inference must pass after startup.

## Migration Plan

Run local backend, frontend, migration, and container verification against the production-based candidate. Record the live image and configuration. Verify backup and rollback on an isolated database copy. Keep the serving process running during build. Perform a bounded drain and stop-first replacement with independent recovery. Verify both public domains, schema, account policies, and authenticated inference before declaring success.
