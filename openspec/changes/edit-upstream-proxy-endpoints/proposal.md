## Why

Upstream proxy endpoints can be created and tested from the dashboard, but
they cannot be corrected or removed from the dashboard.

## What Changes

- Add an authenticated dashboard mutation for updating an existing upstream
  proxy endpoint.
- Add an Edit action that reuses the endpoint dialog with current values.
- Add a confirmed Delete action for endpoints that are not members of a pool.
- Preserve the stored password when the edit form leaves the password blank,
  while never returning the password to the browser.
- Invalidate resolved upstream routes after an endpoint update or deletion.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `upstream-proxy-routing`: Let dashboard operators update and safely delete
  existing proxy endpoints.

## Impact

- Affected code: settings API/schema, dashboard proxy settings form, client
  mutation, translations, and focused tests.
- No database migration or new dependency is required.
