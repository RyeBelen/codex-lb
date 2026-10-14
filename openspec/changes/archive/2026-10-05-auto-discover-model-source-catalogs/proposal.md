# Automatic Model Source catalogs

## Why
Blank configured model IDs should discover provider models and advertised metadata periodically without losing automatic ownership after the first fetch.

## What Changes
- Persist automatic mode and backfill historical empty sources.
- Refresh enabled automatic sources at startup and every five minutes under the existing scheduler leader gate, independent of subscription registry refresh.
- Validate bounded responses, reconcile metadata and preserve caches on failures or concurrent operator edits.
- Allow blank IDs in dialogs, show discovered models, and disable provider-owned metadata controls.

## Impact
Model Source database/API contracts, catalogs, scheduler and dashboard. Local implementation only; no commit, push, deployment, or live calls.
