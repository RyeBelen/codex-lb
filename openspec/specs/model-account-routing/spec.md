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
Authenticated dashboard users SHALL view an account's current allowed-model selections and resolved supported subscription models from that account's detail view. Dashboard writers SHALL atomically replace all allowed-model selections for one account. No selection SHALL mean the account is unrestricted and can serve every model it otherwise supports; one or more selections SHALL restrict the account to those exact model IDs. The editor SHALL render the resolved models as checkboxes, explain empty-selection behavior, support explicit save/reload, and honor read-only access. A selected model that is no longer in the resolved catalog SHALL remain visible as unavailable and removable. When the account catalog is unavailable, the dashboard SHALL distinguish that state from an empty resolved catalog and SHALL NOT offer a write based on missing catalog evidence. The previous global Settings editor SHALL NOT be presented, while the existing model-oriented backend API SHALL remain compatible.

#### Scenario: Show the resolved account catalog
- **WHEN** an authenticated user opens an account whose model catalog is resolved
- **THEN** the account detail shows a checkbox for each supported subscription model and checks the account's current selections

#### Scenario: Restrict one account to selected models
- **WHEN** a dashboard writer selects Astra and Sol for an account and saves
- **THEN** the account is atomically restricted to Astra and Sol while other accounts' selections remain unchanged

#### Scenario: Clear all selections
- **WHEN** a dashboard writer clears every model checkbox and saves
- **THEN** all model grants for that account are removed and the account returns to ordinary eligibility for every model it supports

#### Scenario: Keep stale selections visible
- **WHEN** a selected model is absent from the account's current resolved catalog
- **THEN** the editor shows the model as an unavailable checked selection that the writer can remove

#### Scenario: Account catalog unavailable
- **WHEN** no resolved or retained model catalog exists for the account
- **THEN** the editor reports that the catalog is unavailable and does not allow a replacement write

#### Scenario: Reject invalid account update
- **WHEN** a writer submits a newly selected model outside the account's resolved catalog, names an unknown or pending-deletion account, or a read-only viewer submits an update
- **THEN** the update fails without changing any stored grants

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
