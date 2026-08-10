## ADDED Requirements

### Requirement: APIs page compares top API-key users by daily usage

The APIs page SHALL render separate daily cost and daily token line charts for the latest 30-day UTC calendar window. Each chart SHALL show no more than 10 API-key series, SHALL identify each series by API-key name, and SHALL rank its series independently by the corresponding total usage over that window. API keys with zero usage for a chart's metric SHALL be omitted from that chart.

#### Scenario: Daily charts show the top 10 keys per metric

- **WHEN** more than 10 API keys have recorded cost or token usage during the latest 30-day UTC window
- **THEN** the daily cost chart renders the 10 keys with the highest total cost in that window
- **AND** the daily token chart renders the 10 keys with the highest total token usage in that window
- **AND** neither chart renders an eleventh line

#### Scenario: Sparse usage is displayed as a continuous daily series

- **WHEN** a top API key has no usage on one or more days inside the 30-day UTC window
- **THEN** its line contains a zero-valued point for each missing day
- **AND** both charts cover the same 30 calendar dates, including the current partial UTC day

#### Scenario: Empty metrics do not create empty series

- **WHEN** an API key has zero total cost in the window but non-zero token usage
- **THEN** it is eligible for the daily token chart
- **AND** it is omitted from the daily cost chart

### Requirement: Dashboard exposes bounded daily API-key usage series

The authenticated dashboard API SHALL expose one read-only API-key daily-usage response for the latest 30-day UTC calendar window. The response SHALL contain independently ranked cost and token series, SHALL contain no more than 10 series per metric, SHALL identify each series by API-key id and name, and SHALL return one zero-filled point per calendar day for every included series.

#### Scenario: Daily usage endpoint returns bounded named series

- **WHEN** an authenticated dashboard client requests the API-key daily-usage endpoint
- **THEN** the response identifies the inclusive UTC start and end dates
- **AND** each cost and token series contains the API-key id, API-key name, and 30 dated values
- **AND** each metric contains at most 10 series

#### Scenario: Deleted and internal warm-up activity is excluded

- **WHEN** request history contains activity for an API key that no longer exists or activity classified as internal warm-up
- **THEN** that activity does not contribute to the daily API-key usage series
