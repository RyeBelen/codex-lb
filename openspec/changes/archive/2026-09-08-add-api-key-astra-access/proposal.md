## Why

Administrators need to reserve GPT-6 Astra for explicitly authorized API keys. An unrestricted model allowlist currently permits every available model.

## What Changes

- Add an Allow GPT-6 Astra switch to API key creation and editing.
- **BREAKING**: Existing and new keys default to Astra access disabled; only explicitly enabled keys may request Astra.
- Enforce permission after model overrides and exclude Astra from unauthorized client catalogs.

## Capabilities

### New Capabilities

### Modified Capabilities

- `api-keys`: Persist and enforce explicit per-key Astra permission.

## Impact

API key database migration, management schemas and service, proxy request policy and model catalogs, dashboard forms, and regression tests.
