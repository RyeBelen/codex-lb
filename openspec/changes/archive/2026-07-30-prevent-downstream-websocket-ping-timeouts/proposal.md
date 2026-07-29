## Why

Production Codex Desktop WebSocket sessions are being closed by codex-lb's
Uvicorn server with code `1011` after the default pong watchdog reports
`keepalive ping timeout`. This interrupts otherwise healthy long turns and
causes visible `Reconnecting 5/5` loops even though the application and upstream
account remain healthy.

## What Changes

- Keep protocol pings enabled on client-facing Responses WebSockets so reverse
  proxies continue to observe transport activity.
- Disable the Uvicorn pong-deadline watchdog by default and rely on codex-lb's
  bounded downstream-idle and pending-request budgets for cleanup.
- Expose canonical CLI and environment overrides for the Uvicorn WebSocket ping
  interval and timeout, including an explicit disabled timeout value.
- Add server-configuration and real-protocol regression coverage for a client
  that does not answer a ping while a Responses request remains active.
- Document the production diagnostic signature and rollout monitoring.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `responses-api-compat`: Define client-facing WebSocket liveness behavior,
  configuration, and bounded cleanup when pong acknowledgements are delayed or
  absent.

## Impact

- Affected code: `app/cli.py` Uvicorn startup configuration.
- Affected tests: CLI configuration coverage and a protocol-level Uvicorn
  WebSocket regression.
- Affected operations: Dokploy receives one exact-tag rebuild/restart; the
  existing `/var/lib/codex-lb` volume and database schema are unchanged.
- Public request and response schemas are unchanged.
