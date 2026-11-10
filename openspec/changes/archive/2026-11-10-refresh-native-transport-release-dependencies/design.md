## Context

See proposal.md for the CI failures. The production service already runs the native queue fix. Its immutable image and live SQLite data must remain recoverable while the Git release is prepared.

## Goals / Non-Goals

Resolve the audit findings with compatible dependency updates and keep application contracts unchanged. Do not suppress advisories or expand this patch into application refactoring.

## Decisions

Use rustls 0.23.46, tokio 1.51.6, and hyper 1.9.0 as the smallest compatible direct-version changes addressing the reported Rust findings. Update the affected rustls-webpki and zstd transitive packages to their fixed versions. Keep the existing TLS provider and WebSocket forks.

Update only aiohttp, brotli, certifi, and dnspython in the Python lockfile, subject to their existing dependency constraints. Aiohttp also requires a compatible yarl update. Add zlib1g to the runtime image's existing Debian security-upgrade list.

Preserve source-level behavior rather than weaken audit policy. For example, hyper 1.9.0 removes the unmaintained pin-utils dependency without an advisory allowlist.

## Risks / Trade-offs

Transport dependencies can alter TLS, decompression, or scheduling behavior. Mitigate this through the Rust workspace checks, native wire regression, complete cloud application tests, a separate Git-built staging instance, and real inference/continuation/compaction probes.

## Migration Plan

Keep production on the verified hotfix during validation. Merge only after the actual current-head gates pass. Supervise any production Git rebuild outside model inference, using stop-first updates and automatic Swarm rollback. Explicit recovery pins the currently deployed fixed image and retains the live database. Enable Git auto-deploy only after the Git release is healthy and the production branch contains the fix.
