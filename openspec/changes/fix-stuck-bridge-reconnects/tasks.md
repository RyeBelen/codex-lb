## 1. Bridge startup lifecycle

- [x] 1.1 Adapt the upstream visible stale-holder repair and cover visible/non-visible holders
- [x] 1.2 Record successful upstream-send time and add the validated 120-second response-created timeout
- [x] 1.3 Enforce the timeout in downstream SSE and upstream reader paths without limiting active generation

## 2. Verification and rollout

- [x] 2.1 Add focused regression tests for terminal timeout, fail-all cleanup, healthy active streams, and gate release
- [x] 2.2 Run strict OpenSpec validation, lint/type checks, and focused bridge suites
- [x] 2.3 Deploy once from the tested fix branch, verify health and reconnect/error logs, and disconnect automatic source deploys until the PR stack merges
