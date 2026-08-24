## Context

See `proposal.md` for motivation. API-key validation is cached and runs on the proxy authentication dependency, while normal request-log writes are detached from the response path. The implementation must therefore avoid relying on cached capture counters and must not add request-log database latency to upstream responses. Request-log list APIs are available to read-only dashboard principals, so sensitive payloads cannot be embedded in the existing list response.

## Goals / Non-Goals

**Goals:**

- Atomically bound capture counts across concurrent requests and multiple replicas.
- Keep payload capture off the upstream response critical path except for the explicitly armed diagnostic write.
- Make captured content discoverable from normal request details while preserving admin-only access.
- Reuse request-log retention and API-key deletion semantics for cleanup.

**Non-Goals:**

- Always-on payload logging or response-body capture.
- Capturing multipart file bodies, credentials, headers, or WebSocket frames.
- Reconstructing complete conversations from captured request fragments.

## Decisions

### Use a database counter as the single source of truth

Add `verbose_capture_remaining` to `api_keys`. The dashboard action sets it to a validated count or zero. Capture eligibility does not consult `ApiKeyData` from the authentication cache; it issues a conditional database update (`remaining > 0`) that decrements and returns the new count. This makes one database row the concurrency boundary across processes and replicas.

Alternative considered: an in-memory counter. It was rejected because replica-local counters can over-capture and restart with stale state.

### Persist captures atomically in a dedicated table

The authentication dependency reads only non-empty JSON request bodies. In one transaction it conditionally decrements the key counter and inserts an `api_key_verbose_captures` row containing the bounded body and request metadata. The capture is correlated to the normal request log through the existing API-key ID and stable request identifier. A unique request-identifier/key constraint prevents duplicate dependency evaluation from storing the same inbound request twice.

Alternative considered: carry the payload in a context variable and add it to the later request-log insert. That keeps the authentication path cheaper but can consume a slot without durably storing the input if detached persistence fails, so it does not satisfy the bounded "next N" contract.

### Keep payload content out of list responses

Request-log list entries gain only `hasCapturedInput`. A separate captured-input endpoint takes the request-log ID, resolves its API-key/request-identifier pair, requires administrator access, and returns the stored method, path, content type, body, capture time, and truncation flag. The detail dialog fetches it only after an administrator selects a captured request.

Alternative considered: include payload text directly in every list item. It was rejected because it exposes sensitive content to read-only guests and increases polling bandwidth.

### Bound capture size at 256 KiB and preserve UTF-8 validity

The body is truncated by encoded byte length, then decoded on a valid UTF-8 boundary. The capture records whether truncation occurred. Only content types representing JSON are eligible; headers and multipart data are excluded entirely.

### Integrate cleanup with request-log retention

The capture row has an API-key foreign key with `ON DELETE CASCADE`. During request-log retention, captures older than the same effective cutoff are deleted in the retention transaction. Correlation uses the indexed API-key/request-identifier pair, avoiding any write or lookup on the normal request-log persistence path.

## Risks / Trade-offs

- [Armed capture adds one synchronous database transaction to eligible requests] -> This cost exists only during an explicitly bounded diagnostic window; the normal path performs no capture query when the key counter is zero only if a fast cached hint is safe, otherwise it still needs a conditional update. Prefer one conditional update that returns no row so correctness does not depend on cache state.
- [Request content may contain secrets or personal data] -> Require explicit admin action, cap count and size, exclude headers and multipart bodies, restrict payload reads to admins, audit control changes, and apply retention.
- [A request may be captured but never produce a normal request log] -> Retain the orphan by request ID for diagnosis and remove it at the request-log retention cutoff.
- [Two normal log rows may share a request identifier due to retries] -> Both log rows resolve to the same unique inbound-request capture for that key/request identifier.

## Migration Plan

1. Add the API-key counter and capture table with zero/default-safe values and indexes/foreign keys.
2. Deploy backend support; existing keys remain unarmed and existing request-log responses remain compatible through a default-false presence flag.
3. Deploy dashboard controls and lazy detail fetch.
4. Rollback by removing the UI/control path first, then reverting the schema migration; no existing authentication or accounting fields are changed.
