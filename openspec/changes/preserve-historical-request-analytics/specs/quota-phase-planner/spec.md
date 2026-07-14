## ADDED Requirements

### Requirement: Quota planning uses complete compacted demand history

Quota-planner warmup cost observations and 15-minute demand bins MUST combine
compact facts with retained raw rows for the full configured planning window.
Account, API-key, model, reasoning-effort, request-kind, status, token, cost,
soft-delete, and bucket-boundary semantics MUST remain unchanged.

#### Scenario: Planning window crosses raw retention

- **WHEN** a 28-day planning window contains compact and raw requests
- **THEN** every qualifying request contributes to the same 15-minute demand bin as before pruning
- **AND** warmup costs remain unchanged

