## ADDED Requirements

### Requirement: Blank configured models select durable automatic mode
The system SHALL persist automatic ownership separately from effective models and expose `autoDiscoverModels` in dashboard responses. Empty model inputs SHALL enable automatic mode while retaining cached rows until successful refresh. Nonempty inputs SHALL select manual mode. Omitted updates SHALL preserve mode and cache. Migration SHALL backfill historical empty sources as automatic and nonempty sources as manual.

#### Scenario: cache does not change ownership
- **WHEN** an automatic source receives discovered rows and is reopened or restarted
- **THEN** it remains automatic with blank configured model input
- **AND** unrelated edits preserve its cache

#### Scenario: manual source changes to automatic
- **WHEN** the operator clears a manual list
- **THEN** cached models remain until successful discovery
- **AND** entering a nonempty list restores manual mode

### Requirement: Automatic catalogs refresh under owned leader lifecycle
Enabled automatic OpenAI-compatible sources SHALL refresh on startup and subsequent five-minute passes under the existing leader gate, independently of active accounts and `model_registry_enabled`. Manual or disabled sources MUST NOT fetch. Network I/O SHALL run outside transactions with bounded duration, bytes and model count. Shutdown or leadership loss SHALL cancel owned work. One source failure MUST NOT prevent other refreshes.

#### Scenario: independent of subscriptions
- **GIVEN** no active accounts and subscription registry disabled
- **WHEN** a leader refresh runs
- **THEN** enabled automatic sources are refreshed

#### Scenario: lifecycle owns work
- **WHEN** the process is a follower or stops during refresh
- **THEN** it performs no further discovery writes after cancellation

### Requirement: Provider metadata updates effective models atomically
Discovery SHALL GET `/models` relative to the source base URL using existing source authorization, validate the complete JSON `data` list and IDs, deduplicate deterministically, and map supported advertised display/description, context/output limits, streaming/tools/vision/reasoning and explicit-unit pricing metadata. Missing metadata SHALL use existing safe defaults or unknown prices without name-based inference. Remote source IDs, credentials and server-only request overrides MUST NOT enter cache. Source protocol capabilities SHALL remain operator controlled. Reconciliation SHALL retain surviving row IDs and disabled states and remove missing models.

#### Scenario: supported metadata and access
- **WHEN** discovery returns a valid catalog with supported metadata
- **THEN** effective catalogs and pricing use that metadata
- **AND** existing whitelist, source assignments and model restrictions still apply

#### Scenario: failure and empty response
- **WHEN** network, authentication, validation or persistence fails
- **THEN** the old catalog remains intact
- **AND** a valid empty list clears models while retaining automatic mode

#### Scenario: concurrent operator update
- **WHEN** configuration, credentials, enabled state or manual models change during fetch
- **THEN** the stale result is discarded atomically without overwriting the update

### Requirement: Model Source dialogs explain automatic ownership
Forms SHALL allow blank model IDs and explain five-minute discovery. Automatic sources SHALL show effective discovered models and keep configured IDs blank. Provider-owned metadata controls SHALL be disabled or read-only while automatic, while protocol/key settings stay editable and vertical scrolling remains usable. Visible source lists SHALL periodically refetch cached dashboard data while enabled automatic sources exist, without fetching providers through dashboard reads.

#### Scenario: unrelated automatic edit
- **WHEN** the operator edits a non-model setting
- **THEN** discovered IDs are not submitted as manual configuration

#### Scenario: blank creation
- **WHEN** a valid source is saved with blank models
- **THEN** it is saved as automatic without validation error
