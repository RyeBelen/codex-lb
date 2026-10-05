# Model Source Routing Specification

## Purpose

Define capability-based routing and accounting for OpenAI-compatible model sources, including field-preserving embeddings forwarding.
## Requirements
### Requirement: Model sources declare an embeddings capability

Each model source MUST carry a persisted `supports_embeddings` boolean
capability flag. The flag MUST default to disabled, so a source created or
migrated without an explicit value MUST NOT be treated as embeddings-capable.
The model-source create, read, and update contracts MUST expose the flag, and
the stored value MUST survive a round trip through those contracts.

#### Scenario: existing sources default to disabled

- **GIVEN** a model source row that predates the embeddings capability
- **WHEN** the schema migration runs
- **THEN** the source reports `supports_embeddings` as disabled
- **AND** its existing chat-completions, responses, and audio-transcription
  routing is unchanged

#### Scenario: capability round-trips through the API

- **WHEN** a client creates or updates a model source with the embeddings
  capability enabled
- **THEN** reading the source back reports the capability as enabled

#### Scenario: omitted capability parses as disabled

- **WHEN** a model-source payload omits `supports_embeddings`
- **THEN** it parses as disabled rather than failing validation

### Requirement: Embeddings route only to capable model sources

The system SHALL expose `POST /v1/embeddings` and MUST serve it only from an
enabled model source of kind `openai_compatible` that declares the embeddings
capability and has the requested model enabled. Embeddings requests MUST NOT
fall back to subscription-backed accounts. When the caller presents an API key
restricted to a set of sources, selection MUST stay inside that set. Beyond
the validated `model` and `input` fields, the request payload MUST be
forwarded to the source verbatim.

#### Scenario: capable source serves the request

- **GIVEN** an enabled model source declaring the embeddings capability with
  the requested model enabled
- **WHEN** a client posts to `/v1/embeddings`
- **THEN** the proxy forwards the payload to that source's `/embeddings`
  endpoint and returns the upstream JSON response

#### Scenario: no capable source is a model error

- **GIVEN** no enabled model source declares the embeddings capability for
  the requested model
- **WHEN** a client posts to `/v1/embeddings`
- **THEN** the proxy returns 404 with an OpenAI-format error envelope using
  code `model_not_found`
- **AND** the request is not routed to a subscription-backed account

#### Scenario: source-restricted API key cannot escape its set

- **GIVEN** an API key restricted to a set of model sources
- **WHEN** the only embeddings-capable source for the model is outside that
  set
- **THEN** the proxy returns `model_not_found`

### Requirement: Embeddings requests are accounted like other source routes

Embeddings responses MUST be inspected for prompt and total token usage. When
the caller's API key requires usage for settlement and the source response
reports none, the proxy MUST fail closed with `usage_unavailable` rather than
serving unmetered traffic. Every embeddings attempt that is dispatched to a
model source MUST produce a request-log entry, with `success` on a forwarded
response and `error` on a forwarding, usage, or settlement failure. That entry
MUST carry the upstream status code when a source returned an HTTP response,
and MUST record the upstream status as absent when the attempt failed before
any response was received. A request rejected before source selection succeeds
is not a dispatched attempt: it MUST NOT produce a request-log entry, because
no source was contacted and no reservation was consumed.

#### Scenario: missing usage fails closed for a limited key

- **GIVEN** an API key whose reservation requires reported usage
- **WHEN** the model source returns an embeddings response without a usage
  object
- **THEN** the proxy returns an error envelope using code `usage_unavailable`
- **AND** records an error request log

#### Scenario: forwarding error propagates the upstream status

- **WHEN** the model source returns an error status for an embeddings request
- **THEN** the proxy returns an OpenAI-format error envelope with that status
- **AND** records an error request log carrying the upstream status code

#### Scenario: transport failure records an attempt without an upstream status

- **WHEN** the request to the model source fails before any HTTP response is
  received
- **THEN** the proxy records an error request log for the attempt with no
  upstream status code

#### Scenario: unroutable model is not a logged attempt

- **GIVEN** no enabled model source declares the embeddings capability for
  the requested model
- **WHEN** a client posts to `/v1/embeddings`
- **THEN** the proxy returns the `model_not_found` envelope without writing a
  request-log entry
- **AND** no reservation is consumed for the rejected request

### Requirement: Embeddings source forwarding preserves field presence

For source-routed `POST /v1/embeddings` requests, the system MUST preserve both
the values and presence of fields beyond the validated `model` and `input`
fields. A field explicitly supplied as null MUST be forwarded as null, a field
omitted by the client MUST remain absent, and a non-null field MUST be forwarded
unchanged. This forwarding behavior MUST NOT change reservation settlement or
request-log metadata.

#### Scenario: explicit null extras remain present

- **WHEN** a client supplies `dimensions: null` and `user: null` in a
  source-routed embeddings request
- **THEN** the compatible source receives both keys with null values

#### Scenario: omitted extras remain absent

- **WHEN** a client omits `dimensions` and `user` from a source-routed
  embeddings request
- **THEN** the compatible source payload does not contain either key

#### Scenario: non-null extras and accounting remain unchanged

- **WHEN** a client supplies non-null embedding extras through a limited API
  key
- **THEN** the compatible source receives those values unchanged
- **AND** the reservation settles from reported usage
- **AND** the successful request log retains its model-source metadata and
  token counts

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
