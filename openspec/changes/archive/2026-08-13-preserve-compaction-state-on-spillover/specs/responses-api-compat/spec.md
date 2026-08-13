## MODIFIED Requirements

### Requirement: Codex compaction triggers are bridged into compact output

When `POST /backend-api/codex/responses` receives a request whose top-level `input` array contains exactly one `{"type":"compaction_trigger"}` item as its final element, the proxy SHALL preserve that trigger and forward the request through the subscription-backed upstream Responses streaming path. It MUST NOT translate the request into a standalone `/responses/compact` call.

The proxy MUST relay the upstream compaction SSE lifecycle through the Codex route without synthesizing a replacement response or compaction item. Upstream event ordering, sequence numbers, compaction item identifiers, status, and encrypted content MUST be preserved.

Client-supplied server-side compaction controls, including `context_management`, MUST be forwarded unchanged. A later Responses input containing a genuine upstream `compaction` or `reasoning` item with non-empty `encrypted_content` MUST preserve that item unchanged on every pre-visible upstream attempt. Soft account affinity MUST prefer its existing account but MUST NOT turn encrypted state into a hard account pin. When capacity or quota recovery selects another account before any downstream-visible output, the proxy MUST send the encrypted item to that account unchanged. If upstream rejects the opaque state, the proxy MUST surface the failure rather than fabricate a replacement or silently delete the compacted context.

For Codex-affinity standalone compact requests, `POST /backend-api/codex/responses/compact` SHALL normalize an upstream remote-compaction-v2 response that includes historical message output plus a compaction summary into the single compact output item required by Codex clients. A non-empty upstream compaction item `id` or `status` MUST be preserved in that normalized output item.

OpenAI-style `/v1/responses/compact` is unchanged by this requirement.

#### Scenario: terminal trigger emits a complete compact lifecycle
- **WHEN** a `POST /backend-api/codex/responses` request ends with exactly one top-level `compaction_trigger`
- **THEN** the proxy forwards the trigger unchanged through the normal upstream Responses stream
- **AND** it does not call the standalone compact endpoint

#### Scenario: encrypted compaction item identity survives trigger streaming
- **WHEN** the upstream Responses stream emits compaction lifecycle events for a terminal trigger
- **THEN** the Codex route relays those events without synthesizing replacements
- **AND** upstream sequence numbers, compaction item ID, status, and encrypted content are preserved

#### Scenario: server-side compaction controls survive forwarding
- **WHEN** a Responses request supplies `context_management` with a compaction threshold
- **THEN** the proxy forwards that control unchanged to the subscription-backed upstream

#### Scenario: quota failover retains encrypted compacted state
- **GIVEN** a soft-affinity Responses request contains an upstream-produced compaction item with encrypted content
- **WHEN** the preferred account reports a pre-visible quota failure and the proxy retries another eligible account
- **THEN** both upstream attempts contain the same compaction item and encrypted content
- **AND** the proxy does not hard-fail merely because the selected account changed

#### Scenario: alternate account rejects encrypted compacted state
- **WHEN** a pre-visible spillover account rejects preserved encrypted compacted state
- **THEN** the proxy surfaces the upstream failure
- **AND** it does not silently strip the compaction item or fabricate equivalent context

#### Scenario: malformed trigger placement is rejected
- **WHEN** a `POST /backend-api/codex/responses` request contains a duplicated or non-terminal top-level `compaction_trigger` item
- **THEN** the proxy returns HTTP 400 with `invalid_request_error`
- **AND** it does not attempt upstream Responses or standalone compact handling

#### Scenario: Codex-affinity standalone compact normalizes remote v2 output
- **WHEN** a Codex-affinity `POST /backend-api/codex/responses/compact` request receives upstream output that contains historical message items and one compaction summary item
- **THEN** the JSON response body contains exactly one `output` item for that compaction summary
- **AND** the normalized item preserves the compaction summary's non-empty upstream ID and status
- **AND** it does not expose historical message items as standalone compact output
