## ADDED Requirements

### Requirement: Historical reports remain exact after raw retention

Reports and dashboard aggregate readers MUST combine compact facts with retained
raw rows while preserving arbitrary half-open ranges, IANA timezone day
boundaries, account/model/user-agent filters, warmup exclusion, exact distinct
active-account counts, exact daily median TTFT/TPS, error breakdowns, and
earliest activity. Diagnostic request-log readers MUST remain raw-only.

#### Scenario: Timezone report crosses retention boundary

- **WHEN** a report in any supported IANA timezone contains compact and raw rows
- **THEN** each request contributes to the same local day and metric as before pruning

#### Scenario: Median spans compact and raw rows

- **WHEN** valid TTFT or TPS samples for one report day exist in both stores
- **THEN** the result is the exact median of all qualifying per-request samples

#### Scenario: Old diagnostic row stays hidden

- **WHEN** a compact fact predates raw retention
- **THEN** it contributes to aggregates
- **AND** it does not appear in request-log list, detail, search, or facets

