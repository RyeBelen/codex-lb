## Why

Catalog support does not express an operator's usage budget. An operator needs to reserve GPT-6 for selected Pro accounts while leaving other models available across the ordinary account pool.

## What Changes

- Add explicit model-to-account routing allowlists, with unrestricted routing by default.
- Add dashboard management with individual account selection and a Select Pro shortcut.
- Intersect rules with account grants, key account assignments, model capability, quota, and health eligibility. Retry and reused connections must respect committed rules.

## Capabilities

### New Capabilities

- `model-account-routing`: Persist and manage exact-model account restrictions and enforce them before account selection and inference submission.

### Modified Capabilities

None.

## Impact

Additive database migration, dashboard API and settings section, and the existing proxy account access checks. No rules are enabled automatically and production deployment is separate from local implementation.
