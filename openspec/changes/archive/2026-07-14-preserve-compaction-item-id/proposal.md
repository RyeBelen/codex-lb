## Why

Codex remote compaction output can contain encrypted content that is cryptographically bound to the provider-owned compaction item ID. The proxy currently discards that ID while normalizing the output, causing Codex clients to synthesize a different ID and permanently fail later turns with `invalid_encrypted_content`.

## What Changes

- Preserve a valid upstream compaction item `id` alongside `type` and `encrypted_content` during normalization.
- Emit the same preserved compaction item in the synthetic SSE `response.output_item.done` and terminal `response.completed` events.
- Retain legacy compatibility for upstream compaction payloads that do not include an item ID.
- Add regression coverage for both provider-ID preservation and the legacy ID-less shape.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: Require provider-owned compaction item IDs to survive compact response normalization and synthetic Responses SSE emission.

## Impact

- Affected code: `app/modules/proxy/api.py` compaction normalization and synthetic response handling.
- Affected tests: proxy compaction contract, compact endpoint, and Responses SSE integration coverage.
- Affected clients: Codex tasks that auto-compact through `/backend-api/codex/responses` or `/backend-api/codex/responses/compact`.
- No database, migration, dependency, or public configuration changes.
