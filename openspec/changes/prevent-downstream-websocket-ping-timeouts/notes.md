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
