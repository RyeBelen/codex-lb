## Why

Pool membership is managed in a separate dialog, while endpoint edit, delete,
and test actions crowd the summary list. Pools cannot be edited or deleted.

## What Changes

- Add guarded pool update and delete endpoints. Pool updates change its name,
  active state, and selected members atomically without resetting retained
  member settings.
- Open a pool modal by clicking its name. Manage membership, save, and confirm
  deletion there. Remove the separate Add member action.
- Open an endpoint modal by clicking its name. Edit, test, and confirm deletion
  there, leaving the list as a summary.

## Capabilities

### Modified Capabilities

- `upstream-proxy-routing`: Operators can manage proxy pools and endpoints
  through their respective modals with safe update and deletion behavior.

## Impact

- Settings API, frontend proxy settings, translations, and focused tests.
- No database migration or new dependency.
