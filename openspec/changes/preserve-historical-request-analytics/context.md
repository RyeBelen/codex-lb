## Purpose and scope

This change separates short-lived diagnostic storage from durable analytical
history. Raw request logs remain the detailed operational surface for seven
days. Compact facts retain only fields required to reproduce current aggregate,
planning, limit-accounting, and continuity behavior exactly.

## Rationale

Ordinary daily aggregates are insufficient because report days follow caller
timezones, medians and distinct accounts are non-additive, API-key cost limits
round each request independently, and response ownership depends on individual
ordered identities. A narrow fact is therefore an exact historical aggregate
input rather than a second diagnostic log.

## Concrete example

A June 26 request restored from the pre-prune snapshot is not visible in the
request-log table or detail API. It still contributes exactly once to a Manila
June 26 report, a UTC June 25/26 boundary where applicable, a monthly API-key
limit, a 15-minute quota-planner bin, and a scoped previous-response owner
lookup.

## Failure modes and operations

- Projection or delete parity mismatch rolls back and keeps raw rows.
- Missing/invalid snapshot schema or checksum prevents backfill.
- Backfill reruns insert zero rows after a successful first run.
- Account hard-delete removes facts; soft-delete anonymizes attribution.
- Staging uses a separate environment volume instance, standard authentication,
  and disabled production-affecting schedulers while test data is seeded.
- Production rollout requires a fresh online backup and explicit approval after
  staging parity; code-only rollback is not allowed after schema migration.

## Related contracts

Normative behavior is defined by the delta specs for historical request
analytics, data retention, runtime observability, API keys, Responses API
compatibility, quota planning, and database migrations.
