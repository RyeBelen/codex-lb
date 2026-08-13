## Context

The Codex route currently recognizes a terminal `compaction_trigger`, converts the request to `ResponsesCompactRequest`, calls the standalone upstream `/codex/responses/compact` endpoint, and synthesizes an SSE response. Current Codex clients use remote compaction v2 on the normal Responses stream, while the standalone upstream endpoint returns 404. The latest `clb-upstream` main branch still contains the same compatibility bridge.

## Goals / Non-Goals

**Goals:**

- Use the existing subscription-backed Responses stream for remote compaction v2.
- Preserve trigger validation, account affinity, reservation settlement, and raw Codex SSE behavior.
- Delete the obsolete conversion and synthetic stream code.

**Non-Goals:**

- Emulate compaction inside codex-lb.
- Change explicit `/responses/compact` routes.
- Add a fallback, feature flag, dependency, or setting.

## Decisions

1. Remove only the terminal-trigger branch inside the shared Responses stream handler. Valid trigger requests then continue through the same HTTP/WebSocket streaming path as every other Codex Responses request. This reuses existing routing, retry, logging, and settlement behavior.
2. Keep terminal-trigger detection at the public Codex route. It prevents external model-source routing and retains the existing fail-closed validation for duplicated or non-terminal triggers.
3. Relay upstream SSE unchanged. A fallback to standalone compact was rejected because that endpoint is the observed 404 source; synthetic events also discard upstream protocol fidelity.
4. Keep standalone compact routes and normalization for explicit callers. Their contract is separate from Codex remote compaction v2.

## Risks / Trade-offs

- [Risk] An older upstream that does not support remote compaction v2 will return its own error. → Preserve that error rather than retrying an endpoint known to be unavailable; rollback is a single code revert.
- [Risk] Removing local compact trimming changes the request-size ceiling for trigger requests. → Let the normal Responses transport enforce its existing wire limit, matching the endpoint actually receiving the request.

## Migration Plan

Deploy the proxy change, send a terminal-trigger request through `/backend-api/codex/responses`, and verify that the upstream compaction SSE completes without a standalone compact request. Roll back the change if the selected upstream does not support remote compaction v2.
