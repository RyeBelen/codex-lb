## Why

Production HTTP bridge requests can hold the response-create gate without ever
receiving `response.created`. The proxy keeps downstream clients alive until
Railway closes the connection near five minutes, causing repeated Codex
"Reconnecting" loops and starving later requests on the same session.

## What Changes

- Retire stale gate holders even after a downstream keepalive made them visible.
- Bound the post-send wait for `response.created` below the ingress cutoff and
  fail pending work with a terminal structured error instead of endless keepalives.
- Add regression coverage for visible stale holders and both HTTP/WebSocket
  response-created watchdog paths.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `proxy-admission-control`: Bound pre-created bridge stalls and enforce the
  existing visible stale-holder retirement contract.

## Impact

The fix is limited to HTTP response bridge state, receive-timeout calculation,
one validated setting, and proxy regression tests. Public request and response
schemas remain unchanged except that a previously hanging request now receives
a terminal `response_created_timeout` error before the platform disconnects it.
