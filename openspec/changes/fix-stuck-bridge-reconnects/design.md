## Context

Production evidence showed HTTP bridge requests holding a response-create gate
for more than 591 seconds without `response.created`. The downstream generator
kept emitting 10-second keepalives, so Railway eventually closed otherwise-200
responses around 301-304 seconds and Codex reconnected. The existing stale
holder check excludes `downstream_visible` work even though the normative spec
explicitly requires visible stale work to be retired.

## Goals / Non-Goals

**Goals:**

- Retire visible and non-visible stale gate holders under the existing guard.
- Bound only the pre-created phase after an upstream send, without imposing a
  short limit on valid long-running generation after `response.created`.
- Produce a terminal structured error before the platform disconnects the
  client and release all affected gate/session state.

**Non-Goals:**

- Changing the overall two-hour bridge request budget.
- Treating long active generations as stale.
- Solving upstream account exhaustion or eliminating the one reconnect caused
  by a deliberate single-replica deployment.

## Decisions

- Adapt the existing upstream repair rather than create a new retry model. The
  stale-holder clause is corrected to match the current main spec.
- Record `upstream_sent_at` immediately after each successful bridge send. The
  watchdog starts from this timestamp, not request creation, so queue and gate
  admission time cannot consume the upstream response-created allowance.
- Use a 120-second default. This is generous for `response.created` but remains
  below the observed Railway ingress cutoff near 300 seconds.
- Enforce the deadline in both the downstream SSE event wait and the shared
  upstream WebSocket reader. The reader timeout uses `fail_all_pending` so a
  lone stalled request is cleaned even when no later gate waiter arrives.
- Once `response.created` clears `awaiting_response_created`, the watchdog no
  longer applies; ordinary stream idle and total request budgets remain the
  only active limits.

## Risks / Trade-offs

- [A severely delayed upstream acceptance now fails at 120 seconds] -> The
  previous behavior was an incomplete stream forcibly closed around 300
  seconds; the new failure is earlier, explicit, retryable, and releases state.
- [Two watchdog observation paths could race] -> Existing idempotent pending
  failure/session cleanup owns finalization; tests cover terminal behavior and
  gate release rather than assuming one path always wins.
- [Deploying the fix cuts current streams once] -> Perform one controlled
  deployment after tests and stop source/config churn.
