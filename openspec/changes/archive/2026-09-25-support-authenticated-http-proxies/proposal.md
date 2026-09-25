# Support authenticated HTTP proxies

## Why

Webshare's proxy port accepts authenticated HTTP `CONNECT` but not TLS to the
proxy. The dashboard currently allows credentials only with `https`, so a valid
Webshare endpoint fails its test with `ConnectError`.

## What changes

- Allow credentials on HTTP proxy endpoints in dashboard writes and route
  resolution. Keep credentialed SOCKS endpoints rejected.
- Continue to require HTTPS/WSS upstream targets for credentialed routes and
  send proxy authentication only to the proxy on `CONNECT`.
- Cover dashboard create, edit, test, and routed transport behavior with
  synthetic credentials.

## Impact

HTTP proxy authentication is sent in plaintext between codex-lb and the proxy.
The upstream HTTPS/WSS tunnel remains encrypted. No new setting, migration, or
dependency is needed.
