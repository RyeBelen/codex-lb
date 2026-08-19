## Context

The existing shared classifier recognizes canonical `previous_response_not_found` errors and the older `invalid_request_error` shape only when `param=previous_response_id` and the message says the response was not found. All HTTP bridge and direct WebSocket recovery paths use that classifier.

## Goals / Non-Goals

**Goals:**

- Recognize the observed upstream shorthand at the shared classification boundary.
- Preserve all existing replay, masking, and diagnostics behavior.

**Non-Goals:**

- Change account selection, continuation ownership, or retry policy.
- Broadly reinterpret arbitrary `invalid_request_error` messages.

## Decisions

- Extend the shared classifier instead of individual transports so every existing recovery caller receives the fix.
- Match the normalized observed message narrowly when `param` is absent and the shared caller supplies either no code or the normalized `invalid_request_error` type. A broad substring match could hide unrelated client payload errors.
- Change an existing Codex-native WebSocket integration fixture to the production envelope because canonical error shapes already have separate coverage.

## Risks / Trade-offs

- Upstream may introduce another spelling later → keep canonical code/param handling authoritative and add observed spellings only with regression evidence.
- A malformed client-supplied anchor may use the same shorthand → existing safe-replay checks still decide whether to replay or fail with a sanitized continuity error.

## Migration Plan

Deploy as a normal proxy patch. Roll back the commit if the narrow classifier produces unexpected continuity rewrites; no stored data changes are involved.
