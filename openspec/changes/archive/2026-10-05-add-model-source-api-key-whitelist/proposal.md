## Why

Operators can assign sources from an API key, but cannot reserve a Model Source
for selected keys. Model Source dialogs also exceed short viewports without
providing vertical scrolling.

## What Changes

- Persist a per-source API-key whitelist; an empty selection allows all callers
  subject to existing restrictions.
- Filter source discovery and every source routing capability by that whitelist.
- Add selection to source create/edit dialogs and make those dialogs scroll
  vertically within the viewport.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `model-source-routing`: source-level API-key eligibility and dashboard controls.

## Impact

One compatible migration, source contracts, source selection/catalog filtering,
and the existing dashboard dialogs. No dependency, configuration flag, or
production rollout is included.
