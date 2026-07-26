## Why

The main dashboard becomes difficult to use when a deployment contains many unavailable or migrated accounts because account cards and quota charts render every status together. Operators need the fork's status filtering behavior on the upstream-based Dokploy deployment without reintroducing the rest of the divergent fork.

## What Changes

- Add a multi-select account-status filter above the main dashboard account-card grid.
- Add the same status filtering capability above the five-hour and weekly usage charts.
- Default both dashboard views to routable or temporarily unavailable statuses while excluding deactivated and re-auth-required accounts.
- Preserve upstream v1.22.0 internationalization and accessibility behavior.
- Add focused component tests for filtering, dynamic status options, empty selections, and filtered chart totals.

## Capabilities

### New Capabilities

- `dashboard-account-status-filtering`: Defines status-filter behavior for dashboard account cards and account quota charts.

### Modified Capabilities

None.

## Impact

- Affects dashboard React components and frontend component tests while reusing the existing English/Korean/Chinese locale resources.
- Does not change backend APIs, database schema, account routing, or API-key behavior.
- Requires a custom image derived from the pinned upstream v1.22.0 release for the Dokploy deployment.
