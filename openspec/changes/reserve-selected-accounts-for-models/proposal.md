## Why

The current model allowlist leaves its selected accounts available to every other model. The operator intended to reserve those accounts for the selected model, protecting their usage from unrelated requests.

## What Changes

- Reserve accounts selected in model rules for the models explicitly assigned to them.
- Exclude reserved accounts from all other model requests, including retries, reused connections, and background inference.
- Explain both routing directions in the settings editor and verify saved production selections remain intact.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-account-routing`: Account reservations restrict which models may consume usage on selected accounts.

## Impact

Model-routing repository filtering, settings wording, and regression tests. Existing grant rows are reused. No new database migration is required. Existing configured accounts become reserved when the corrected code is deployed.
