## Context

See `proposal.md` for motivation. The deployed server starts Uvicorn
programmatically from `app/cli.py` and currently forwards the HTTP keep-alive
timeout and WebSocket message-size budget, but not Uvicorn's WebSocket ping
settings. Uvicorn therefore uses a 20-second ping interval and a 20-second pong
timeout on the client-facing socket.

The upstream OpenAI WebSocket already keeps pings enabled while disabling its
pong watchdog. Client-facing sockets additionally have an application-owned
120-second idle timeout when no request is pending, and pending turns are
bounded by stream and total request budgets.

## Goals / Non-Goals

**Goals:**

- Prevent the protocol server from closing active Codex turns solely because a
  pong was delayed or lost.
- Preserve transport pings for reverse-proxy liveness.
- Keep abandoned sockets bounded through existing application-owned cleanup.
- Give operators one canonical CLI/environment contract for both ping values.

**Non-Goals:**

- Changing upstream OpenAI WebSocket retry or replay behavior.
- Changing Responses request/response schemas.
- Extending stream or total request budgets.
- Masking network disconnects that are observed through normal read/write
  failure.

## Decisions

### Keep pings enabled and disable only the default pong deadline

`ws_ping_interval` remains `20.0` seconds by default, while
`ws_ping_timeout` defaults to `None`. This mirrors the upstream transport
policy: intermediaries continue to observe frames, but protocol-level pong
timing does not outrank application request state.

Disabling pings entirely was rejected because idle reverse proxies can then
mistake a long reasoning turn for a dead connection. Merely increasing the pong
timeout was rejected as the default because it still creates a second,
transport-owned request deadline that can conflict with the explicit
application budgets.

### Use canonical Uvicorn-prefixed configuration

`app/cli.py` will expose:

- `--ws-ping-interval` / `UVICORN_WS_PING_INTERVAL`
- `--ws-ping-timeout` / `UVICORN_WS_PING_TIMEOUT`

Each setting accepts a positive finite number of seconds or the case-insensitive
value `none`. The interval defaults to `20`; the timeout defaults to `none`.
Flags inherit argparse's precedence over environment-derived defaults.

A shared parser will reject NaN, infinity, zero, negative, and non-numeric
enabled values before importing or starting Uvicorn.

### Test both configuration and protocol behavior

Unit tests will assert default, environment, flag-precedence, disabled, and
invalid-value behavior at `app.cli.main()`. A protocol-level test will run a
real Uvicorn WebSocket server with a short ping interval and disabled pong
timeout, connect a client that deliberately suppresses pong replies, wait beyond
the historical deadline, and prove the socket still carries application data.

## Risks / Trade-offs

- [A genuinely dead client is no longer retired by Uvicorn's pong deadline] →
  Sockets without pending work still close after the application idle timeout;
  pending work remains bounded by stream/total budgets, and ordinary socket
  read/write failures still terminate immediately.
- [Operators configure an excessively long or disabled ping interval] → The
  setting is explicit and validated; operations guidance retains the default
  interval for reverse-proxy liveness.
- [A dependency upgrade changes `None` semantics] → Unit coverage verifies the
  exact arguments forwarded to Uvicorn, and the protocol regression exercises
  the installed server implementation.

## Migration Plan

1. Run focused CLI and real-WebSocket tests, followed by lint, typing, and the
   relevant integration suite.
2. Push an exact fork tag and create an in-volume SQLite backup before
   deployment.
3. Rebuild/restart the Dokploy compose service without changing its named
   volume.
4. Verify health, a long WebSocket turn, and the absence of new
   `keepalive ping timeout` closures.
5. Roll back to `dokploy-weekly-quota-active-fix-d46afef0` if readiness or
   Responses traffic regresses; restore the backup only if integrity changes,
   which this schema-free change does not require.
