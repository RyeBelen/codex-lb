## Context

The fork added local multi-select filters to dashboard account cards and usage donuts. Upstream v1.22.0 retained the reusable `MultiSelectFilter` component but removed those two uses while adding internationalization and a list/card account-view toggle. The Dokploy deployment is intentionally based on upstream v1.22.0, so the feature must be reapplied as a narrow frontend-only patch.

## Goals / Non-Goals

**Goals:**

- Restore status filtering for the dashboard account-card grid and quota donuts.
- Keep the controls compatible with upstream localization, privacy, accessibility, and chart behavior.
- Derive filter choices from observed account statuses while retaining the standard routable/temporary status choices.
- Recalculate donut capacity and remaining-credit center values from the visible subset.

**Non-Goals:**

- Change account status, routing, API behavior, or persistence.
- Add server-side filtering or URL-persisted filter state.
- Filter the account summary line or list-mode table in this focused port.
- Reintroduce unrelated fork behavior.

## Decisions

### Keep filter state local to each dashboard surface

Account cards and quota donuts receive independent local multi-select state, matching the proven fork behavior. This avoids expanding `DashboardPage` state or coupling account-card visibility to quota-chart exploration.

Alternative considered: one global filter in `DashboardPage`. It was rejected because it would change list-mode and summary semantics beyond the requested port and create a broader regression surface.

### Default to operational statuses

Both filters start with `active`, `paused`, `rate_limited`, and `quota_exceeded`. Re-auth-required, deactivated, and future statuses remain selectable when present but do not dominate the initial dashboard.

### Preserve mathematically consistent donut values

When a filter hides accounts, chart items, total capacity, and center remaining credits are recomputed from the same subset. The existing full totals remain in use when all items are visible.

### Use existing i18n status vocabulary

The control label uses `dashboard.filters.statuses`; option labels map raw account statuses through `normalizeStatus` and existing `common.status.*` translations, falling back to formatted slugs for future statuses.

## Risks / Trade-offs

- [Independent controls can show different subsets] → Keep the controls visibly attached to their respective sections and use identical defaults.
- [A future status lacks a translation] → Fall back to `formatSlug(status)` while retaining the raw value for filtering.
- [Filtered donut totals can be misleading if only segments are filtered] → Recompute capacity and center values from the filtered items and cover the calculation with component tests.
