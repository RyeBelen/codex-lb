## Context

The native Codex Responses route supports both Codex clients and OpenAI SDK clients. Classification currently treats any OpenAI-shaped payload that accepts `text/event-stream` as an SDK request, even when native Codex transport headers are present. During upstream silence this selects the public comment heartbeat (`: keepalive`) instead of the native `codex.keepalive` data event. Codex parses only data-bearing SSE events for its idle watchdog, so repeated comments do not prevent a five-minute disconnect.

## Goals / Non-Goals

**Goals:**

- Preserve native SSE framing whenever the request carries an allowlisted native Codex originator or user-agent.
- Keep OpenAI SDK compatibility behavior unchanged for requests without native signals.
- Cover the misclassification with the real Codex Desktop fingerprint and verify the existing stalled-stream framing tests.

**Non-Goals:**

- Changing upstream HTTP/WebSocket transport selection or image-request routing.
- Changing the configured upstream idle timeout or Codex client timeout.
- Adding a new first-upstream-event watchdog or changing request-log settlement semantics.

## Decisions

- Reuse the existing native Codex identity predicate rather than duplicate the allowlisted originators and user-agent prefixes in the API module. Continuity headers such as `x-codex-turn-state` are deliberately excluded because SDK clients can replay them.
- Keep explicit SDK signals (`x-stainless-*` or an OpenAI SDK user-agent) authoritative. Evaluate native Codex identity after those signals but before generic payload-shape and `Accept` heuristics. A native request may legitimately use the OpenAI Responses shape and event-stream accept header; those fields describe its wire shape, not its client contract.
- Add a focused classification matrix with the real Codex Desktop fingerprint, Codex CLI identity, generic SDK-shaped traffic, and conflicting Stainless/native signals. Existing stalled-stream tests continue proving that native contract mode emits `codex.keepalive` while public SDK mode emits comment keepalives.

Concrete example: `originator: Codex Desktop` plus `Accept: text/event-stream` and `{model, input, stream}` remains a native stream and receives `event: codex.keepalive` while upstream is silent.

## Risks / Trade-offs

- [A third-party client spoofs a native Codex identity and receives vendor events] -> Reuse only the existing narrow originator and user-agent allowlists already trusted by upstream request normalization.
- [Changing precedence breaks OpenAI SDK clients that forward Codex headers] -> Treat explicit native transport identity as authoritative; ordinary SDK requests do not send those headers and retain the existing heuristic path.
- [A helper import creates a module cycle] -> Keep the reusable predicate in the lower-level core client module and import it into the API edge, which already imports from that module.

## Migration Plan

Deploy the classification and regression test together. No data or configuration migration is required. Rollback is a normal code rollback; public `/v1/responses` remains unaffected.

## Open Questions

None.
