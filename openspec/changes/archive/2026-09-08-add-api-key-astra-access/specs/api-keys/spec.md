## ADDED Requirements

### Requirement: Explicit Astra access

The system MUST persist an `allowGpt6Astra` boolean per API key, defaulting to false for existing and new keys. API key create, update, list, and regenerate responses MUST expose this setting. An omitted update MUST preserve the setting. The dashboard MUST provide an accessible Allow GPT-6 Astra switch in create and edit forms.

The proxy MUST reject requests whose effective model is `gpt-6-astra` unless the authenticated API key has this setting enabled, including requests with authentication disabled. The restriction MUST apply after enforced-model resolution on Responses, compact, Chat Completions, and WebSocket requests and before upstream work or quota reservation. Enabled keys MUST remain subject to existing allowlists, account/source scope, quotas, and model availability.

Client model catalogs MUST omit Astra for callers without permission, including Codex metadata catalogs regardless of Apply to codex /model. Administrator model selection MUST still offer available Astra so administrators can configure keys.

#### Scenario: Default access denied

- **WHEN** an existing or newly created key has not been explicitly enabled for Astra
- **THEN** Astra requests return the existing model-not-allowed error and client catalogs omit Astra

#### Scenario: Enable and revoke access

- **WHEN** an administrator enables Astra for one key
- **THEN** that key can request and discover available Astra subject to other restrictions, while other keys remain denied
- **AND** disabling the setting invalidates cached authorization through the existing cache-invalidation mechanism

#### Scenario: Enforced model cannot bypass permission

- **WHEN** a disabled key enforces Astra but the client requests a different model
- **THEN** the effective Astra request is rejected before upstream work

#### Scenario: Unrelated updates preserve permission

- **WHEN** an administrator renames an enabled key without submitting the Astra setting
- **THEN** Astra permission remains enabled

#### Scenario: No authenticated key

- **WHEN** a caller requests Astra while proxy authentication is disabled
- **THEN** the request is rejected and Astra is omitted from the caller's model catalogs
