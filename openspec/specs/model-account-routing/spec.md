# model-account-routing Specification

## Purpose
The system SHALL enforce operator-selected upstream account allowlists for individual model IDs.
## Requirements
### Requirement: Explicit model account scope
The system SHALL support an account allowlist for each normalized exact model ID. A model with no restriction SHALL use existing routing eligibility. A restricted model with no permitted accounts SHALL have no eligible account. Model account scope SHALL intersect with API-key account scope, account grants, discovered model capability, health, and quota eligibility. No fallback SHALL send a restricted model to an account outside its allowlist. Rules SHALL apply to the effective model after model enforcement.

#### Scenario: Reserve GPT-6
- **GIVEN** GPT-6 is restricted to selected Pro accounts and Sol has no restriction
- **WHEN** clients request each model
- **THEN** GPT-6 only uses those selected accounts and Sol retains its normal account pool

#### Scenario: No available permitted account
- **WHEN** every permitted account is exhausted, unavailable, or excluded by another scope
- **THEN** the request fails without inference on an unlisted account

### Requirement: Dashboard rule management
Authenticated dashboard users SHALL list model rules. Dashboard writers SHALL atomically replace a model policy, validate account IDs, and restore unrestricted routing. Invalid writes SHALL preserve the previous policy. The settings dashboard SHALL support individual account selection, a shortcut selecting the currently listed Pro accounts, explicit save/reload, an empty restricted selection warning, and read-only behavior. The shortcut SHALL NOT automatically grant future Pro accounts access.

#### Scenario: Save selected Pro accounts
- **WHEN** a writer selects Pro accounts and saves a rule
- **THEN** the selected account IDs persist and newly imported accounts are not automatically added

#### Scenario: Reject invalid policy
- **WHEN** a writer names an unknown or pending-deletion account, or a read-only viewer submits a policy
- **THEN** the update fails without changing the stored rule

### Requirement: Fresh routing enforcement
HTTP inference, retries, compact requests, transcription, warm-up, and subsequent requests on reused HTTP bridge and WebSocket connections SHALL check committed model scope before upstream submission. A revoked pinned account SHALL fail without transferring its account-bound state. Access denials SHALL NOT penalize account health. Requests already submitted SHALL retain their existing completion and settlement behavior. Realtime attachment SHALL apply model scope when a model is known for the call.

#### Scenario: Revoke a reused connection
- **GIVEN** a connection previously used account A for model M
- **WHEN** A is removed from M's policy and another request is submitted
- **THEN** that request does not reach upstream on A

#### Scenario: Background inference respects model scope
- **WHEN** a limit warm-up, quota-planner probe, or automation ping targets an account outside the model allowlist
- **THEN** the job fails without sending inference to that account

### Requirement: Safe policy persistence
The migration SHALL preserve existing data and create no default restrictions. Deleting or requesting deletion of an account SHALL remove its eligibility without removing the model policy. Downgrade SHALL preserve existing account and API-key data.

#### Scenario: Delete the last allowed account
- **WHEN** the last account permitted for a model is deleted
- **THEN** the model remains restricted with no eligible accounts
