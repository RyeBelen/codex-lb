## Why

Server-side compaction returns opaque encrypted state that carries the useful context into later Responses requests. Codex LB already preserves this state, but the contract does not say what happens when soft affinity moves a pre-visible request to another subscription account.

## What Changes

- Require client-supplied server-side compaction controls and genuine upstream encrypted items to survive forwarding unchanged.
- Keep encrypted state best-effort rather than turning it into a hard account pin.
- Preserve the same encrypted input during pre-visible quota or capacity spillover; surface an upstream rejection rather than inventing missing context.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: Define best-effort encrypted compaction continuity across soft-affinity spillover.

## Impact

- Responses compatibility specification
- Sticky-account integration coverage
- No production code, setting, dependency, route, or database change
