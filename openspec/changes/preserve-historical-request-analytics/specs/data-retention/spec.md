## MODIFIED Requirements

### Requirement: Retention is opt-in and validated

Retention MUST be disabled by default. `request_log_retention_days` and `usage_history_retention_days` MUST accept `0` (disabled) or values at or above their safety floors (7 days for request logs, 45 days for usage history); configurations between 1 and the floor MUST be rejected at startup.

#### Scenario: Default configuration deletes nothing

- **GIVEN** neither retention setting is configured
- **WHEN** the retention job runs
- **THEN** no rows are deleted from `request_logs`, `usage_history`, or `additional_usage_history`

#### Scenario: Unsafe retention values fail fast

- **WHEN** an operator sets `request_log_retention_days=6` or `usage_history_retention_days=10`
- **THEN** settings validation MUST raise an error at startup naming the violated floor

### Requirement: Request-log pruning never deletes unfolded rows

Request-log pruning MUST run only while the fold is current (watermark within two fold lags of now) and MUST select only rows with `requested_at` older than the retention cutoff AND at least one fold lag below the watermark, so concurrent lifetime-summary readers holding a slightly older watermark can never lose rows from a just-folded window. Before deleting a bounded selected batch, pruning MUST insert compact historical facts for the exact selected ids and verify every selected id is represented. Projection and exact-id deletion MUST commit in one transaction, and any projection/delete parity failure MUST roll back. When no rollup watermark exists, or the fold is catching up (initial backfill, stalled scheduler), request-log pruning MUST be skipped.

#### Scenario: Unfolded rows survive pruning

- **GIVEN** a request-log row older than the retention cutoff whose `requested_at` is above the fold watermark
- **WHEN** the retention job runs
- **THEN** the row MUST NOT be deleted

#### Scenario: Stalled fold suspends pruning

- **GIVEN** a fold watermark older than two fold lags
- **WHEN** the retention job runs with request-log retention enabled
- **THEN** no `request_logs` rows are deleted

#### Scenario: Lifetime totals are unchanged by pruning

- **GIVEN** folded request-log rows older than the retention cutoff
- **WHEN** the retention job deletes them and account usage summaries are read afterwards
- **THEN** per-account lifetime totals MUST equal their pre-pruning values

#### Scenario: Pruning is skipped before the first fold

- **GIVEN** no `account_usage_rollup_state` row exists
- **WHEN** the retention job runs with request-log retention enabled
- **THEN** no `request_logs` rows are deleted

#### Scenario: Projection parity fails

- **GIVEN** a bounded selected batch cannot be represented exactly in compact history
- **WHEN** the retention transaction verifies selected, projected, and deleted ids
- **THEN** the transaction MUST roll back
- **AND** every selected raw row MUST remain

### Requirement: Retention runs leader-gated in bounded batches

The retention job MUST run on at most one instance at a time and MUST project and delete in bounded batches, each committed in its own transaction, so a large backlog never holds one long transaction.

#### Scenario: Backlog is pruned incrementally

- **GIVEN** more prunable rows than one batch
- **WHEN** a retention pass runs
- **THEN** rows are projected and deleted across multiple bounded transactions until no prunable raw rows remain

