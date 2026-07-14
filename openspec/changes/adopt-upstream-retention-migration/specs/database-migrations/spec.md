## ADDED Requirements

### Requirement: Retired fork retention lineage upgrades to upstream

The migration bootstrap MUST recognize the deployed fork retention revision
and remap it to the last shared upstream ancestor. The compatibility migration
MUST validate the hardened legacy table, require an epoch upstream fold
watermark, import already-pruned account and API-key lifetime sums exactly once,
verify parity, and drop the legacy table only after verification succeeds.

#### Scenario: Production fork database upgrades

- **GIVEN** a database stamped at the hardened fork retention revision
- **WHEN** it upgrades to upstream head
- **THEN** the migration reaches one head with no schema drift
- **AND** imported lifetime totals equal the legacy aggregate totals
- **AND** retained raw request logs remain present

#### Scenario: Invalid legacy state fails closed

- **GIVEN** required hardened columns are missing or the upstream watermark is not at epoch
- **WHEN** the compatibility migration runs
- **THEN** migration fails explicitly
- **AND** the legacy aggregate table is not dropped

