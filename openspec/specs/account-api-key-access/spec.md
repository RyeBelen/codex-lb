# Account API key access

## Purpose

Reserve upstream accounts for explicitly permitted API keys while retaining independent per-key account scope.

## Requirements

### Requirement: Account access policy
Accounts SHALL default to shared API-key access. Restricted accounts SHALL accept client inference only from explicitly granted API keys. A restricted account with no grants SHALL deny all client inference, including requests without an API key. Existing key account scope SHALL remain an additional restriction. Changing account grants MUST NOT change key account assignments or key scope flags.

#### Scenario: New key cannot use a reserved account
- **GIVEN** account A is restricted to key X
- **WHEN** existing key Y, a newly created key, or a request without a key requests inference
- **THEN** account A is ineligible

#### Scenario: Independent scope intersection
- **GIVEN** account A grants key X access and key X is scoped to account B
- **WHEN** X requests inference
- **THEN** X cannot use A
- **AND** editing A's grants does not change X's assigned accounts

#### Scenario: Empty grants and deletion remain restricted
- **WHEN** the last permitted key is removed or deleted
- **THEN** the account remains restricted and no client can use it

### Requirement: Dashboard access management
Authenticated dashboard writers SHALL read and atomically replace an account's access policy through its access endpoint. The endpoint SHALL validate account and key IDs, reject malformed policies, and preserve the prior policy on invalid updates. The accounts dashboard SHALL expose Shared and Restricted modes, key selection, save state, and read-only behavior. Shared mode SHALL clear inactive grants.

#### Scenario: Save and reload
- **WHEN** a writer saves Restricted with selected API keys and reloads the account
- **THEN** the same policy and selections are displayed

#### Scenario: Invalid update
- **WHEN** a policy names an unknown key or a read-only viewer attempts a write
- **THEN** the update fails without changing the stored policy

### Requirement: Routing and connection enforcement
Account access SHALL constrain HTTP inference, native and compatible routes, WebSocket turns, file operations, compact requests, warm-up, and retries before upstream inference. Sticky affinity, pinned files, single-account routing, and existing connections MUST NOT bypass access. Each subsequent request on a reused connection SHALL observe committed account access changes. Requests already sent upstream MAY finish. A forbidden pinned owner SHALL fail without moving its account-bound state to another account.

#### Scenario: Retry stays within the permitted pool
- **WHEN** a permitted account fails and a forbidden account is otherwise healthy
- **THEN** retry never sends inference to the forbidden account

#### Scenario: Revoke an existing connection
- **GIVEN** a key has an open connection to account A
- **WHEN** its grant is revoked and another request is submitted
- **THEN** the new request is not sent to A

### Requirement: Account-backed client reads
Client account-pool usage and reset-credit reads and operations SHALL exclude accounts forbidden to the key. Account grants SHALL NOT alter independent model-source permissions. Dashboard administration and background account maintenance SHALL retain their existing authority.

#### Scenario: Private account quota
- **WHEN** a key requests account-pool usage or reset credits
- **THEN** forbidden accounts are excluded from the returned pool and cannot be targeted for reset

### Requirement: Compatible migration
The migration SHALL preserve existing account and key data, initialize existing accounts as shared, and maintain a single Alembic head. Grant rows SHALL be removed when their account or API key is deleted.

#### Scenario: Upgrade existing database
- **WHEN** a database containing accounts and scoped keys is upgraded
- **THEN** those accounts remain shared and the keys retain their assignments
