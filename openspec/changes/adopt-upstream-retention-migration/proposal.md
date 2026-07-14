## Why

The production fork is stamped at a retired request-log aggregate revision,
while upstream now provides the long-term retention implementation. A direct
upstream deployment fails startup because that revision is unknown.

## What Changes

- Merge upstream retention and remove the fork-only daily aggregate runtime.
- Remap the deployed fork revision to its shared upstream ancestor.
- Import already-pruned account and API-key lifetime sums into upstream
  rollups, verify parity, then remove the retired table.

## Capabilities

### Modified Capabilities

- `database-migrations`: add a fail-closed compatibility upgrade for the
  retired fork retention lineage.

## Impact

Production uses upstream's disabled-by-default retention contract and its
30-day request-log safety floor. Existing pruned lifetime totals are retained.

