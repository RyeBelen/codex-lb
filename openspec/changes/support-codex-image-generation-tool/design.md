## Context

`ResponsesRequest` and `V1ResponsesRequest` currently share one built-in tool validator. That shared path rejects `image_generation`, which is still correct for `/v1/responses` and chat-completions compatibility, but it is too strict for backend Codex traffic. `/backend-api/codex/responses` uses the shared validator in three places: the HTTP route body model, websocket `response.create` normalization, and the internal bridge HTTP owner-handoff route.

## Goals / Non-Goals

**Goals:**

- Accept `image_generation` for backend Codex Responses HTTP and websocket requests.
- Preserve the same backend-only acceptance when HTTP bridge owner handoff revalidates the forwarded request on `/internal/bridge/responses`.
- Keep `/v1/responses` and `/v1/chat/completions` rejecting `image_generation`.
- Keep the shared normalization behavior for aliases like `web_search_preview`.

**Non-Goals:**

- Allow additional built-in tool types such as `file_search`, `code_interpreter`, or `computer_use`.
- Change upstream tool rewriting beyond the backend-specific validation allowance.
- Broaden OpenAI-style `/v1/*` compatibility contracts.

## Decisions

### Route-scoped tool validation context

The shared tool validator will accept an explicit allowlist of built-in tool types instead of mutating the global unsupported set. Backend Codex call paths will opt into `image_generation`; OpenAI-style `/v1` and chat paths will continue using the default strict behavior.

This keeps one normalization function and avoids duplicating the tool canonicalization logic in multiple models.

### Manual backend HTTP parsing

The backend HTTP route and internal bridge route will validate raw JSON payloads through the shared normalization helper instead of relying on FastAPI body parsing straight into `ResponsesRequest`. That allows the backend routes to pass their route-specific tool policy while preserving the existing OpenAI error envelope behavior on validation failures.

This is preferred over weakening the `ResponsesRequest` model globally, which would unintentionally broaden `/v1` behavior through shared helpers.

### Explicit websocket policy plumbing

`ProxyService.proxy_responses_websocket()` and its request preparation path will receive an explicit backend tool allowlist parameter. The backend websocket route will pass `image_generation`; the `/v1/responses` websocket route will pass no extra allowances.

This keeps websocket policy separate from unrelated flags such as Codex session affinity and avoids coupling tool policy to transport behavior.

## Risks / Trade-offs

- [Risk] Backend-only policy could drift across HTTP, websocket, and internal bridge call paths. → Mitigation: route all three through the same shared validation helper and add regression coverage for HTTP and websocket acceptance.
- [Risk] Manual backend HTTP parsing could change validation envelopes. → Mitigation: reuse the existing `openai_validation_error()` wrapper so backend failures still return the same `invalid_request_error` shape.
- [Risk] Future Codex-only built-in tools may require more route-specific exceptions. → Mitigation: represent the backend allowance as an explicit allowlist so the policy can be extended intentionally instead of relaxing the global unsupported set.
