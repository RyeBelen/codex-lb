## Context

Codex remote compaction returns an encrypted summary whose authentication data can include the output item's provider-owned `id`. The proxy currently reduces compaction output to `type` and `encrypted_content`; when the Codex client receives an ID-less SSE item it assigns a local `cmp_...` ID. Replaying that locally assigned ID with the provider-bound ciphertext causes an unrecoverable `invalid_encrypted_content` response on every later turn.

Both remote-compaction-v2 shapes handled by `_compact_response_output_item()` are affected: an item in `output`, and the fallback `compaction_summary` field. Older upstream payloads may legitimately omit `id` and must remain compatible.

## Goals / Non-Goals

**Goals:**

- Preserve a non-empty upstream compaction `id` without changing it.
- Use one normalized item consistently in standalone compact JSON and synthetic SSE output.
- Keep ID-less legacy compaction payloads working.
- Prove the public compact and SSE contracts with regression tests.

**Non-Goals:**

- Decrypting, inspecting, or rewriting encrypted compaction content.
- Inventing proxy-owned compaction IDs.
- Repairing historical client transcripts inside the service.
- Changing OpenAI-style `/v1/responses/compact` behavior.

## Decisions

1. `_compact_response_output_item()` will conditionally copy `id` only when it is a non-empty string. This keeps the normalized shape minimal while preserving the provider's cryptographic identity when present.
2. The proxy will never synthesize or transform a compaction ID. Only the provider that produced the ciphertext can supply the correct bound identifier.
3. Existing ID-less behavior remains valid for legacy providers. The normalized item omits `id` instead of emitting `null` or an empty string.
4. Tests will assert both the `response.output_item.done.item` and `response.completed.response.output[0]` shapes because divergence between these two SSE events can corrupt client persistence even if the standalone compact endpoint is correct.

## Risks / Trade-offs

- [Provider sends an invalid or stale ID] -> Preserve it unchanged because any proxy rewrite is guaranteed to invalidate bound ciphertext; upstream validation remains authoritative.
- [Legacy clients assume exactly two compaction keys] -> Existing JSON consumers must already tolerate provider response fields, and the ID is emitted only when upstream supplies it; retain explicit ID-less tests.
- [Historical corrupted tasks remain broken after deployment] -> Repair those transcripts separately and reversibly; the service fix prevents new corruption but cannot reconstruct discarded provider IDs.

## Migration Plan

Deploy the proxy-only change after focused contract and integration tests. No data migration is required. Rollback is the previous application revision, though rollback reintroduces corruption for newly generated provider-ID compactions.

## Open Questions

None.
