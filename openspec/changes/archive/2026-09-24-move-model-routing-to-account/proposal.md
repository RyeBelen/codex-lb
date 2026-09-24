## Why

Model-account reservations are currently configured model-first under advanced settings, even though operators reason about them as an account permission alongside API key access. This makes it easy to reserve an account for one model without noticing that every other model is then excluded from that account.

## What Changes

- Move the dashboard editor from Settings > Advanced to each account's detail view as **Allowed models**.
- Populate the editor from the resolved subscription-model catalog for that account and present models as checkboxes.
- Treat no selected models as unrestricted: the account may serve every model it supports. One or more selections restrict the account to those exact models.
- Add one atomic account-oriented read/write API over the existing model-account grant tables.
- Keep unavailable selected models visible for removal, and disable writes when the account catalog is unavailable.
- Retain the existing model-oriented backend API for compatibility while removing its dashboard editor.
- Add no database migration, dependency, setting, or registry persistence field.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-account-routing`: Replace global dashboard rule management with per-account allowed-model management while preserving routing behavior and persistence semantics.

## Impact

- Backend: model-routing repository/service/schemas and account dashboard routes.
- Frontend: account detail, account API/schema, settings cleanup, tests, and mock handlers.
- Documentation: model-account-routing normative spec and context.
- Persistence: existing `model_account_policies` and `model_account_grants` only; no migration.
