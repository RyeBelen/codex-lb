## Context

See proposal.md for motivation. Sources already support dashboard CRUD,
per-capability lookups, and API-key assignments. Proxy discovery and source
selection must agree; operator dashboard catalogs still expose all sources.

## Goals / Non-Goals

Use one access predicate for proxy source catalogs and every source lookup.
Preserve source restrictions independently of key deletion and regeneration.
Keep existing subscription routing and authentication semantics unchanged.

## Decisions

- Store a nullable Text column containing JSON key IDs, following existing
  serialized access-list patterns. NULL and [] mean unrestricted. A cascading
  grants table would require extra state to prevent deletion of the last key
  from removing the restriction; retained IDs avoid that ambiguity.
- Validate new selections against existing keys, deduplicate IDs, and retain
  unavailable IDs already saved on that source. Updating other fields does
  not alter the whitelist.
- Share a fail-closed parser/access predicate across selection and discovery.
  Apply it to ordered matching candidates before choosing the first eligible
  source, rather than rejecting only the first row after SQL LIMIT 1.
- Reuse the existing safe key-list endpoint and checkbox/query controls.
  Apply viewport height and vertical overflow CSS only to the two source dialogs.

## Risks / Trade-offs

- Matching sources are scanned in memory; if catalogs become large, migrate to
  indexed grants while preserving deleted-key restrictions.
- When global API-key authentication is disabled, the existing auth layer
  treats bearer requests as unauthenticated. A nonempty source whitelist denies
  those requests. Operators must enable API-key authentication to identify keys.
- A malformed stored whitelist fails closed instead of broadening access.

## Migration Plan

Upgrade Alembic before serving with the updated app; existing rows remain
unrestricted. Verify selected/unselected catalog and request paths after rollout.
This change is verified locally only. A downgrade drops whitelist configuration,
so any rollback must preserve the operator's configuration and requires separate
production approval. Prefer restoring prior code only after reviewing access
consequences; old application versions do not enforce the new restriction.
