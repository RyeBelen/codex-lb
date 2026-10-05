## ADDED Requirements

### Requirement: Model sources have API-key whitelists

Each Model Source SHALL persist an `allowed_api_key_ids` list exposed through
dashboard create/read/update contracts. An empty list SHALL allow all callers
otherwise permitted by existing access rules. A nonempty list SHALL permit only
authenticated callers whose API-key ID is in that list. Existing sources SHALL
default to an empty list. Omitted update fields SHALL preserve the current list.
Newly selected IDs MUST identify existing API keys. Deleting or making a selected
key unavailable MUST NOT silently broaden a source's access.

#### Scenario: empty selection permits all

- **GIVEN** a source with no selected keys
- **WHEN** an otherwise permitted caller discovers or requests its models
- **THEN** the source whitelist does not restrict that caller

#### Scenario: selected keys restrict access

- **GIVEN** a source with a nonempty whitelist
- **WHEN** an unselected key or unauthenticated caller discovers or requests models
- **THEN** that source is excluded from discovery and forwarding candidates
- **AND** a selected key can use it subject to existing restrictions

#### Scenario: update and deletion preserve restrictions

- **GIVEN** a source with selected key IDs
- **WHEN** an update omits the whitelist or a selected key is deleted
- **THEN** the saved whitelist remains unchanged
- **AND** only explicitly saving an empty selection restores unrestricted access

#### Scenario: unknown new key is rejected

- **WHEN** a create or update selects a new nonexistent key ID
- **THEN** the dashboard API rejects the request without saving any changes

### Requirement: Source whitelist applies to discovery and routing

Source whitelist eligibility SHALL apply to OpenAI and Codex model catalogs,
chat completions, Responses including compact and continuity selection,
audio transcriptions, embeddings, and WebSocket source ownership checks.
Eligibility MUST intersect with existing API-key source assignments and model
restrictions. Candidate filtering MUST occur before choosing a source, so an
ineligible earlier candidate cannot hide an eligible source for the same model.
Restricted source IDs and whitelist contents MUST NOT leak into proxy catalogs.

#### Scenario: another eligible source can serve the model

- **GIVEN** two sources for the same model and only the later source permits a key
- **WHEN** the key requests that model
- **THEN** selection can choose the later eligible source

#### Scenario: source assignments still apply

- **GIVEN** a whitelist permitting a key whose assignments exclude the source
- **WHEN** the key discovers or requests the model
- **THEN** the source remains unavailable to that key

### Requirement: Model Source dialogs expose whitelist and vertical scrolling

Model Source create/edit dialogs SHALL offer accessible API-key selection and
explain that no selection means available to all. Saved selections SHALL load
when editing, including unavailable IDs that operators can explicitly remove.
Loading failures MUST NOT silently clear a saved whitelist. Dialog height MUST
fit within the viewport and contents MUST scroll vertically when they exceed it,
so controls and submission remain reachable on short screens.

#### Scenario: selection round trips through editing

- **WHEN** an operator saves selected keys and reopens the source editor
- **THEN** those keys remain selected
- **AND** explicitly clearing all selections makes the source available to all

#### Scenario: short viewport remains usable

- **GIVEN** a viewport shorter than the Model Source form
- **WHEN** the operator opens create or edit
- **THEN** the dialog fits the viewport and can scroll to the submit control
