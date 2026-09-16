# model-account-routing Specification

## Purpose
The system SHALL reserve selected upstream accounts for assigned models while preserving ordinary eligibility on unreserved accounts.

## Requirements

### Requirement: Explicit model account scope
The system SHALL reserve selected accounts for normalized exact model IDs. An account assigned to one or more model rules SHALL serve only those models. Unreserved accounts SHALL retain ordinary model eligibility. A model SHALL remain eligible to use unreserved accounts in addition to accounts reserved for it. Empty rules SHALL reserve no accounts and SHALL NOT block the model. Model account scope SHALL intersect with API-key account scope, account grants, discovered model capability, health, and quota eligibility. Rules SHALL apply after model enforcement and existing alias normalization. Retries SHALL NOT use an account reserved for another model.

#### Scenario: Reserve accounts for Astra
- **GIVEN** accounts A, B, and C are reserved for Astra and account D is unreserved
- **WHEN** clients request Astra or Sol
- **THEN** Astra can use A, B, C, or D subject to existing eligibility, while Sol cannot use A, B, or C

#### Scenario: Multiple model assignments
- **WHEN** an account is reserved for both Astra and Sol
- **THEN** it can serve Astra and Sol but no other model

#### Scenario: No available permitted account
- **WHEN** all unreserved accounts and all accounts reserved for the requested model are unavailable or excluded
- **THEN** the request fails without inference on an account reserved for another model

### Requirement: Dashboard rule management
Authenticated dashboard users SHALL list model reservations. Dashboard writers SHALL atomically replace a reservation, validate account IDs, and remove reservations. Invalid writes SHALL preserve the previous reservation. The settings dashboard SHALL support individual account selection, a shortcut selecting the currently listed Pro accounts, explicit save/reload, an empty selection explanation, and read-only behavior. The editor SHALL explain that selected accounts serve only their assigned models and that the model can also use other eligible accounts. The shortcut SHALL NOT automatically reserve future Pro accounts.

#### Scenario: Save selected Pro accounts
- **WHEN** a writer selects Pro accounts and saves a reservation
- **THEN** the selected IDs persist and newly imported accounts remain unreserved

#### Scenario: Reject invalid policy
- **WHEN** a writer names an unknown or pending-deletion account, or a read-only viewer submits a policy
- **THEN** the update fails without changing the stored reservation

### Requirement: Fresh routing enforcement
HTTP inference, retries, compact requests, transcription, warm-up, and subsequent requests on reused HTTP bridge and WebSocket connections SHALL check committed account reservations before upstream submission. A pinned account reserved for another model SHALL fail without transferring its account-bound state. Reservation denials SHALL NOT penalize account health. Requests already submitted SHALL retain their existing completion and settlement behavior. Realtime inference with no known model SHALL exclude reserved accounts. Model-less file operations SHALL preserve their existing authorization behavior.

#### Scenario: Reserve an account used by an existing connection
- **GIVEN** a connection used account A for Sol
- **WHEN** A is reserved for Astra and another Sol request is submitted
- **THEN** the request does not reach upstream on A

#### Scenario: Background inference respects reservations
- **WHEN** a limit warm-up, quota-planner probe, or automation ping targets an account reserved for another model
- **THEN** it does not send inference to that account

#### Scenario: Unknown Realtime model
- **WHEN** a Realtime call or attachment has no known model
- **THEN** it cannot use an account reserved for a specific model

### Requirement: Safe policy persistence
Existing selected account IDs SHALL become account reservations without a schema migration. Deleting or requesting deletion of an account SHALL remove that account's eligibility. Removing a model rule SHALL release its selected accounts unless another rule reserves them. Removing the last grant SHALL restore ordinary model eligibility on a surviving account.

#### Scenario: Remove a reservation
- **WHEN** an account's only model reservation is removed
- **THEN** the account can serve other models subject to existing eligibility

#### Scenario: Delete the last reserved account
- **WHEN** the last account in a model reservation is deleted
- **THEN** the deleted account is ineligible and the model can still use other unreserved eligible accounts
