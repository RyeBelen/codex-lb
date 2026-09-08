## Context

See proposal.md for motivation. API keys already have typed create/update data, distributed authorization-cache invalidation, and shared model-access checks. Catalog filtering has separate OpenAI and Codex paths.

## Goals / Non-Goals

Use one persisted permission and the existing management endpoint. No exclusive single-key ownership or changes to upstream entitlement.

## Decisions

Add a non-null boolean with a false database default, rather than expanding allowlists to all current model names. This keeps other models unrestricted as catalogs evolve. Reuse shared request policy for enforcement after model overrides, and filter Astra before building either client catalog. No-key requests are denied because they have no explicit permission. Omitted PATCH fields preserve state; null follows the existing boolean update convention and preserves state.

## Risks / Trade-offs

Existing Astra clients stop working until their key is enabled; this is the explicitly requested default-deny policy. Cache propagation retains the existing bounded invalidation behavior. Active requests are not canceled retroactively.

## Migration Plan

Add a migration after the current Alembic head. Verify existing rows become false and downgrade/upgrade works in an isolated database. Deploy migration before updated workers, then enable selected keys. Example: enable the personal key and leave the shared key disabled; only the personal key can request Astra. Rollback restores the prior unrestricted policy by reverting code and downgrading the new migration.
