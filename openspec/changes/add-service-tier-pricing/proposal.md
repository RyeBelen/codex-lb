## Why

`codex-lb` currently prices requests only by model name, which makes fast-mode (`service_tier: "priority"`) requests look like standard-tier traffic in both API key cost limits and dashboard/request-log cost reporting. The pricing table also lacks `gpt-5.4`, so those requests are undercounted as zero cost.

## What Changes

- add `gpt-5.4` pricing support, including the documented long-context standard tier rates
- make fast-mode pricing depend on `service_tier` so priority requests are costed above standard requests
- persist `service_tier` in request logs so historical cost summaries and trends remain correct

## Impact

- Code: `app/core/usage/pricing.py`, `app/core/usage/logs.py`, `app/modules/api_keys/service.py`, `app/modules/proxy/service.py`, `app/modules/request_logs/repository.py`, `app/modules/usage/builders.py`
- DB: `request_logs.service_tier`
- Tests: pricing, dashboard trends, API key service, request log cost reporting
