## Verification evidence

Validated on Windows with CPython 3.13.14. The test process loaded the virtual
environment's bundled MSVC runtime directories before importing `greenlet`.

- Focused CLI, real-protocol liveness, and application idle-cleanup coverage:
  60 passed.
- Complete Responses WebSocket integration module: 75 passed.
- Full unit suite: 4,905 passed, 61 skipped, and 15 platform/environment-only
  failures.
- Ruff lint and format checks, scoped `ty` checks, and strict OpenSpec
  validation passed.

The 15 full-unit failures are outside this change and match the fork's existing
Windows baseline: POSIX path separator, executable, permission, home-expansion,
and `fork()` assumptions; Windows SQLite file-locking behavior; and host
proxy-environment precedence. The focused CLI and WebSocket tests that exercise
this change passed cleanly.

## Production rollout

- Fork commit: `69b610a9`
- Exact tag: `dokploy-downstream-ws-ping-fix-69b610a9`
- Dokploy container: `30db844529a8`
- Pre-deployment backup:
  `/var/lib/codex-lb/pre-downstream-ws-ping-69b610a9.db`
- Live and backup database integrity: `ok`; retained account count: 102.
- Public readiness and liveness endpoints: HTTP 200; readiness database check:
  `ok`.
- Running defaults: ping interval `20.0`, pong timeout `None`.
- Public authenticated WSS test: stayed connected for 46.1 seconds while two
  server pongs were deliberately suppressed, then completed a client
  ping/pong round trip.
- Post-test log search across 5,000 lines: no `keepalive ping timeout`,
  `sent 1011`, or `ConnectionClosedError` entries.
