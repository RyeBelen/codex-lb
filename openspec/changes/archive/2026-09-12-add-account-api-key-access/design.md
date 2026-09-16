## Context

The existing api_key_accounts relation means a key's outbound scope. It cannot also mean an account's inbound grants: editing one would silently change the other. The proxy already accepts an account ID scope before selection, but long-lived bridges can reuse an account without selecting again.

## Goals / Non-Goals

Implement the access intersection with one normalized source of truth for each independent rule. Preserve dashboard administration and scheduler authority. This change does not introduce account groups or change model-source grants.

## Decisions

- Store api_key_access_restricted on accounts and normalized grants in account_api_key_grants. This is a distinct relationship from key scope, not a duplicated list of the same permissions.
- Use a shared repository policy query and proxy authorization helper. Resolve access from committed database state before selection and before requests on reused transports, avoiding dependence on stale account snapshots or API-key cache entries.
- Apply key scope first and account grants as an intersection. Restricted plus empty means deny all. Shared clears grants.
- Use a dedicated account access endpoint and editor. Validate the whole replacement before a transaction commits. Use foreign keys and cascading deletion.

## Risks / Trade-offs

Fresh policy reads add database work to selection and reused turns. Keep queries narrow and indexed; use one session per operation and never share sessions across concurrent tasks. Do not interrupt already submitted work on revocation. Test pinned owners and failure settlement so denial does not cause a cross-account retry or leak a reservation.

## Migration Plan

Add one forward revision from the current head. Test fresh and populated SQLite upgrades, downgrade/re-upgrade, schema drift, and PostgreSQL locally when available. Existing accounts remain shared. Complete local backend, frontend, and migration checks before deployment. Deployment is a separate operational step.
