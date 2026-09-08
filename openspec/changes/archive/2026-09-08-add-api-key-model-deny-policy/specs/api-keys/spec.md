# API-key model deny policy delta

## ADDED Requirements

### Requirement: API keys support general allow and deny model policies

The system SHALL accept nullable `allowed_models` and `denied_models` lists on
API-key creation and update and SHALL return both fields in API-key responses.
An absent or empty `allowed_models` list MUST allow every model except those in
`denied_models`. A non-empty `allowed_models` list MUST allow only its models,
subject to the denylist. Denied models MUST take precedence over allowed models.
Cursor-style aliases MUST use the same canonical equivalence for allow and deny
checks on subscription models, while model-source selection MUST preserve its
existing exact-slug semantics.

The system MUST reject an API-key configuration when its normalized allowlist
and denylist overlap or when its enforced model is denied. Request validation,
`/api/models`, `/v1/models`, both catalogs in `/backend-api/codex/models`, and
all model-source selection paths MUST apply the effective policy consistently.

The dashboard create and edit dialogs SHALL show Allowed models and Denied
models as checkbox multi-selects. Selecting a model in either control MUST make
it unavailable in the other control. The UI MUST explain that no allowed
models means all models are allowed and that denied models take precedence.
The API-key table SHALL summarize both configured lists.

#### Scenario: Empty allowlist permits all models except denied models

- **GIVEN** an API key has no allowed models and denies `gpt-5.6-astra`
- **WHEN** the key requests any other model
- **THEN** the request is permitted by model policy
- **AND** `gpt-5.6-astra` is rejected and omitted from model catalogs

#### Scenario: Deny rule wins over allow rule

- **GIVEN** an API-key payload contains the same canonical model in both lists
- **WHEN** an admin creates or updates the key
- **THEN** the system rejects the contradictory configuration with HTTP 400

#### Scenario: Denied enforced model is invalid

- **GIVEN** an API-key payload denies its enforced model
- **WHEN** an admin creates or updates the key
- **THEN** the system rejects the configuration with HTTP 400

#### Scenario: Dashboard prevents overlapping selection

- **WHEN** an admin selects a model in Allowed models
- **THEN** that model cannot also be selected in Denied models
