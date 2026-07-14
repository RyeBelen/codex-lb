## MODIFIED Requirements

### Requirement: Foreground routing treats local usage snapshots as non-authoritative

Foreground proxy account selection MUST NOT reject an otherwise active account solely because a local primary/5-hour usage snapshot, synthetic planner cost, or inferred budget pressure reports that the account has reached or exceeded 100 percent usage. A current standard secondary/weekly usage snapshot at or above 100 percent is an exception for standard routing: the selector MUST derive `quota_exceeded` and MUST exclude that account before sticky affinity, reset ordering, or routing strategy evaluation. The weekly decision MUST NOT depend on credit metadata or primary-window availability. Independently gated additional-quota requests retain their documented standard-quota bypass.

#### Scenario: Active account at local primary usage exhaustion is still selectable

- **GIVEN** an upstream account is persisted as active
- **AND** its latest local primary usage snapshot reports 100 percent usage with a future reset
- **AND** its current weekly usage snapshot reports less than 100 percent usage
- **WHEN** foreground account selection evaluates the account
- **THEN** the account remains eligible for upstream routing
- **AND** the selection result does not report a local `Rate limit exceeded` or `no_accounts` failure solely from the primary snapshot

#### Scenario: Active account at current weekly exhaustion is excluded

- **GIVEN** an upstream account is persisted as active
- **AND** its latest current standard weekly usage snapshot reports 100 percent usage with a future reset
- **AND** its primary usage snapshot reports available capacity
- **WHEN** foreground account selection evaluates the account
- **THEN** the derived account state is `quota_exceeded`
- **AND** the account is excluded before sticky affinity and routing-strategy ordering

#### Scenario: Weekly exhaustion is independent of credit metadata

- **GIVEN** an upstream account is persisted as active
- **AND** its latest current standard weekly usage snapshot reports at least 100 percent usage
- **WHEN** foreground account selection evaluates the account with missing, zero, positive, or unlimited credit metadata
- **THEN** every credit-metadata variant is excluded as `quota_exceeded`

#### Scenario: Elapsed weekly snapshot does not remain an account block

- **GIVEN** an upstream account has a stored weekly usage snapshot at 100 percent
- **AND** that snapshot's reset deadline has elapsed
- **WHEN** foreground account selection derives the current usage state
- **THEN** the elapsed snapshot does not keep the account `quota_exceeded`
- **AND** later upstream rate-limit evidence remains governed by upstream retry and backoff metadata
