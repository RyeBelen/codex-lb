## Why

The APIs page shows lifetime per-key breakdowns and a trend for only the selected key, so operators cannot compare how their highest-usage API-key users change from day to day. A bounded top-10 daily view makes that comparison readable without loading or drawing every key.

## What Changes

- Add a dashboard API endpoint that returns zero-filled daily cost and token series for the top 10 API keys over the latest 30-day UTC window.
- Rank cost and token series independently by their totals in that window and omit keys with no usage for the corresponding metric.
- Add daily cost and token multi-line charts to the APIs page overview, with API-key names in the legend and no more than 10 lines per chart.
- Keep chart data loading independent from the selected-key detail queries and retain the existing lazy chart-loading boundary.

## Capabilities

### New Capabilities

### Modified Capabilities

- `frontend-architecture`: Define the APIs-page top-10 daily usage charts and their dashboard API contract.

## Impact

- Backend: API-key repository aggregation, service mapping, response schemas, and a new read-only dashboard route under `/api/api-keys`.
- Frontend: APIs-page data schema/client/hook, overview layout, lazy Recharts chart component, and loading/error presentation.
- Tests: backend aggregation and route coverage plus frontend schema, hook, and component coverage.
