# Missing response-created retry-loop context

## Purpose and scope

The retry circuit is intended to stop repeated hard-affinity pre-response
failures from resubmitting the same continuity-bound request without a recovery
window. This follow-up covers the client-safe
`missing_response_created_timeout` watchdog. It does not change the watchdog
deadline, authorize cross-account replay, or alter soft-affinity routing.

## Decision rationale

The timeout is recorded through the existing hard-affinity circuit rather than
a second timeout-specific cache. It has the same observable safety state as the
already eligible `stream_idle_timeout`: the request has no
`response.created`, no downstream-visible response lifecycle, and no proof that
the selected account is unhealthy. Reusing the circuit preserves one durable
API-key-scoped source of truth across replicas.

Changing the timeout into an account penalty or transparently stripping the
continuity anchor was rejected. Silence does not prove an account failure, and
replaying ambiguous accepted work can duplicate a continuation or side effect.

## Constraints and failure modes

- Only hard-affinity bridge keys may accumulate this failure.
- The timeout remains account-neutral and does not grant replay authority.
- Clean-close jitter remains a fixed two-second implementation bound instead
  of expanding the operator settings surface.
- Durable lookup or persistence failure continues to fall back to local state
  and observability rather than failing the request.
- A successful terminal response clears the accumulated circuit state.
- The circuit deliberately remains half-open after its bounded cooldown so a
  recovered upstream path can be probed.

## Concrete production sequence

An upstream socket first closes before completion, recording
`stream_incomplete` for a hard Codex session. Codex Desktop retries the same
anchored continuation, but upstream emits no `response.created`; after 240
seconds the owner-side watchdog emits `missing_response_created_timeout`.
That second failure now opens the durable circuit. The next eligible
pre-created replay observes the persisted cooldown and is suppressed instead
of immediately repeating the same recovery attempt.

## Operational notes

Monitor `http_bridge_retry_circuit_total` outcomes together with
`missing_response_created_timeout` bridge logs. After rollout, the important
signal is that a missing-created timeout following an incomplete stream is
paired with a circuit-open event for the same hashed hard-affinity key, while
account-health state remains unchanged.
