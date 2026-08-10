## Context

The APIs page currently receives lifetime totals in the API-key list, fetches hourly seven-day trends only for the selected key, and lazy-loads chart code. Comparing many keys by requesting the selected-key trend route repeatedly would introduce a client fan-out and still provide hourly rather than daily data. Request history may span both live and archived rows and must retain the established warm-up exclusion.

## Goals / Non-Goals

**Goals:**

- Aggregate all candidate API-key usage in one repository query and bound the response and rendering to 10 series per metric.
- Use one stable UTC 30-day window and zero-fill missing dates in the service layer.
- Preserve the frontend's asynchronous Recharts boundary and keep this query independent of selected-key state.

**Non-Goals:**

- Add a configurable date picker or ranking limit.
- Replace the selected API key's existing seven-day hourly trend.
- Persist new rollups or add a database migration.

## Decisions

### Aggregate daily buckets once and rank in the service

The repository will group the unified request-history selectable by API-key id and 24-hour UTC epoch bucket, joining current API keys to obtain their names. The service will calculate totals, rank cost and token series independently, select 10 for each metric, and build continuous daily grids.

This keeps database access to one bounded aggregate query and avoids dialect-specific date conversion by reusing the epoch-bucket approach already used for per-key trends. Ranking in Python also allows cost and tokens to select different top keys from the same aggregate result. A client fan-out to the existing trend endpoint was rejected because it scales with the number of keys and returns the wrong granularity.

### Use a fixed latest-30-day UTC contract

The endpoint will cover UTC midnight 29 days before the current UTC date through the current instant, producing 30 inclusive calendar dates. UTC aligns with existing timestamp contracts and makes zero-filling deterministic across browser time zones. A configurable range was rejected because the request only needs daily comparison and adding controls would expand the API and UI contract.

### Add overview charts behind the existing lazy chart boundary

The APIs page will fetch daily usage once, independent of selection, and pass it into the overview. A dynamically imported chart module will render two multi-line charts and shared legend behavior. This keeps Recharts out of the initial entry chunk as required by the existing frontend contract.

## Risks / Trade-offs

- [The aggregate scans 30 days of request history across all API keys] -> Use the existing indexed history path, group in SQL, return only aggregated buckets, and keep the window fixed.
- [Two independently ranked charts may show different sets of keys] -> Label each legend directly and state the metric-specific ranking in chart subtitles.
- [Current-day data is partial] -> Identify the range as UTC and include the current date consistently in both charts.

## Migration Plan

Deploy the additive route and frontend together. No schema migration or backfill is required. Rollback removes the route and overview chart call without affecting stored data or existing selected-key trends.
