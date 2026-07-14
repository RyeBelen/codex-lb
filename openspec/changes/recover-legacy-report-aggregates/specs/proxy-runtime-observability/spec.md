## MODIFIED Requirements

### Requirement: Reports expose recovered historical coverage honestly

The Reports API and dashboard MUST expose available and included legacy
aggregate coverage. Aggregate-only history MUST be included only in UTC report
mode, MUST preserve supported additive report totals, and MUST NOT represent
unavailable per-request speed distributions as zero-valued measurements.

#### Scenario: Operator requests a range containing retired history

- **WHEN** the selected report range overlaps recovered legacy aggregates
- **AND** the active report timezone is not UTC
- **THEN** the dashboard offers an explicit UTC recovered-history mode
- **AND** it explains that request detail and speed medians are unavailable

