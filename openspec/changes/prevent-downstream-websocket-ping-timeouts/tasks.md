## 1. Server Liveness Configuration

- [x] 1.1 Add validated CLI and environment configuration for the client-facing WebSocket ping interval and pong timeout.
- [x] 1.2 Forward the resolved settings to Uvicorn while keeping pings enabled and the pong watchdog disabled by default.

## 2. Regression Coverage

- [x] 2.1 Add unit coverage for defaults, environment values, flag precedence, disabled values, and invalid values.
- [x] 2.2 Add a real-protocol regression proving a non-ponging client remains connected past the historical Uvicorn deadline.
- [x] 2.3 Confirm application-owned downstream idle cleanup remains bounded.

## 3. Verification and Deployment

- [x] 3.1 Run strict OpenSpec validation, focused tests, lint, formatting, and scoped type checks.
- [x] 3.2 Run the broader relevant integration/unit gates and document any environment-only failures.
- [ ] 3.3 Push an exact fork-only deployment tag, create a production database backup, and deploy without changing the named volume.
- [ ] 3.4 Verify readiness, retained data, long WebSocket behavior, and the absence of new server-side keepalive ping timeouts.
- [ ] 3.5 Sync and archive the verified OpenSpec change.
