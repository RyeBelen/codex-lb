## 1. Compaction Contract

- [x] 1.1 Preserve a valid provider-owned `id` in normalized compaction output while retaining the legacy ID-less shape.
- [x] 1.2 Verify the synthetic SSE stream emits the identical normalized compaction item in output-item and completed events.

## 2. Regression Coverage

- [x] 2.1 Add unit coverage for provider-ID preservation and ID-less compatibility.
- [x] 2.2 Add compact endpoint and terminal compaction-trigger integration assertions for provider-ID preservation.

## 3. Validation

- [x] 3.1 Run focused proxy compaction tests and relevant lint/type checks.
- [x] 3.2 Run strict OpenSpec validation and verify implementation against the change artifacts.
