## Context

The Responses request model already forwards unknown supported fields such as `context_management`, and the normal wire serializer preserves genuine `compaction` and `reasoning` items with `encrypted_content`. Soft account affinity prefers the account that handled the prior turn, while bounded pre-visible quota or capacity recovery may select another account.

## Decisions

1. Keep the encrypted item in every pre-visible upstream attempt. The alternate account may be able to consume it, and stripping it eagerly guarantees context loss.
2. Do not upgrade encrypted input to hard ownership. Exhausted subscription quota must still be able to spill to another account.
3. Do not add an automatic ciphertext-stripping retry. No documented upstream error uniquely proves that encrypted state is the rejection cause, and a compacted window may have no equivalent plaintext state to replay.
4. Keep existing verified owner-loss recovery unchanged. It may project opaque response-owned state out only when it has already proved a self-contained account-neutral plaintext replay.

## Risks / Trade-offs

- An alternate account may reject opaque state produced under another account. The proxy surfaces that failure because fabricating or silently deleting the only compacted context would be worse.
- If the upstream accepts the encrypted item across accounts, the full compacted context is preserved with no special proxy state.
