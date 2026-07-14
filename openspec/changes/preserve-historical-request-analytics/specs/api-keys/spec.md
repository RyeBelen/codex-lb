## ADDED Requirements

### Requirement: Bounded API-key analytics survive raw retention

The system MUST make API-key limit initialization, seven-day trends/totals, and
per-account cost views combine compact facts with retained raw rows. Existing successful
request, non-warmup, half-open time-window, optional model, output-token fallback,
cached-token clamp, soft-delete attribution, and per-request micro-dollar floor
semantics MUST remain unchanged.

#### Scenario: New limit spans compact history and raw tail

- **WHEN** a new API-key limit window spans both stores
- **THEN** each qualifying request contributes exactly once
- **AND** the initialized value equals its value before pruning

#### Scenario: Cost rounding remains per request

- **WHEN** qualifying compact facts contain fractional micro-dollar costs
- **THEN** each request cost is floored to integer micro-dollars before summation
