## Context

See `proposal.md` for motivation. Model reservations are stored model-first as policy rows plus `(model, account_id)` grants, while the requested dashboard interaction is account-first. The runtime already interprets zero grants for an account as unrestricted and one or more grants as the exact models that account may serve. The registry snapshot contains model-to-account catalog membership and records accounts whose catalogs were resolved or safely retained.

## Goals / Non-Goals

**Goals:**

- Provide one account-oriented API operation whose save is atomic across all selected models.
- Reuse existing persistence and model-registry evidence without a migration or duplicated catalog state.
- Preserve hidden/stale restrictions as visible removable selections.

**Non-Goals:**

- Change runtime account selection or model eligibility semantics.
- Remove the existing model-oriented backend API.
- Add external model sources to subscription-account routing.
- Add search, bulk account editing, optimistic versioning, or automatic saves.

## Decisions

### Expose account routes from the model-routing module

Add account-oriented routes at `GET` and `PUT /api/accounts/{account_id}/allowed-models`, backed by the existing model-routing context. The route path matches the account-detail ownership operators see, while the service and repository remain inside their existing domain module.

Alternative: make the client invert and rewrite global model rules. Rejected because one account save would become multiple requests that can partially succeed and overwrite concurrent changes.

### Derive the picker from the in-memory resolved registry

Invert the snapshot's model-to-account membership for the requested account, include only API-supported subscription models, and take labels from the resolved model objects. Treat an account present in the snapshot's account-plan index as catalog-resolved, including a legitimately empty or retained stale catalog. If the account is absent, report the catalog as unavailable instead of treating an empty option list as authoritative.

Alternative: derive choices from plan-level or global `/api/models` data. Rejected because those unions can include models the specific account does not advertise.

### Validate against current options plus existing stale selections

A write may contain models currently resolved for the account or models already stored for it. This permits stale selections to remain or be removed but prevents a client from creating a new unsupported selection. Catalog-unavailable writes fail without mutation.

Alternative: accept any syntactically valid model ID as the compatibility API does. Rejected because it would violate the account picker contract and recreate hidden routing exclusions.

### Replace one account's grants in one transaction

Lock and validate the account, delete its existing grants, ensure selected policy rows exist, insert the selected grants, and remove policy rows left without grants. Other accounts' grants remain untouched. The existing writer serialization and database transaction provide the same rollback behavior as model-oriented replacement.

Alternative: store a JSON allowlist on the account. Rejected because it duplicates the existing source of truth and requires a migration.

### Reuse the account-access card interaction pattern

The new card owns its query, local checkbox edits, explicit save mutation, loading/error/read-only states, and cache update. It sits next to API key access. No mode selector is needed because the empty selection itself is the unrestricted mode.

Alternative: keep both global and account editors. Rejected because two dashboard surfaces for the same relation are harder to understand and test.

## Risks / Trade-offs

- **[A catalog can disappear between load and save]** → Recompute and validate the catalog server-side; reject the write rather than apply stale assumptions.
- **[A previously selected model disappears]** → Return selections independently from available choices and render missing selections explicitly.
- **[Legacy clients still use model-oriented writes]** → Keep the existing API and route semantics unchanged.
- **[Empty policy rows outlive the global editor]** → Remove policy rows that become grantless during account-oriented replacement; routing behavior is unchanged.

## Migration Plan

No data migration is required. Deploy backend and frontend together. Existing grants render directly in the account editor. Rollback restores the old dashboard editor against unchanged tables and the retained compatibility API.
