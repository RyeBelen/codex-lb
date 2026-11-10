## Release and diagnosis

The confirmed defect was a scheduling failure in the native transport's two bounded queues. Buffered events could outrun a ready consumer and erase the stream's buffered completion. The WebSocket adapter then classified local consumer backpressure as an upstream/account failure, contributing to account backoff and owner-unavailable continuations. Compaction timing was observed, but the exact original screenshot's underlying exception was not retained. This fix addresses the reproduced transport failure without changing compaction payloads or response ownership.

Implementation commit: `eabe5270c`, `fix(proxy): preserve native stream bursts and account health`.

Production baseline: `a1f2a616007a49f4fe03d975525962441a1d2d05` from `origin/prod`. All four original source hashes matched the running image before the patch was built.

| Artifact | Immutable image ID |
| --- | --- |
| Previous production | `sha256:7607b22ad573424b3682e17f7e1b9b30d024d130cc3bf7687e81a84271d24457` |
| Tested and deployed patch | `sha256:3f1addbd44c2f6194b19c12284986fa5954f1c4f3005f1bf12c45421821f1fd0` |

The candidate derives from the existing runtime and changes only `native_egress.py`, `codex.py`, `proxy.py`, and `proxy_websocket.py`. Dependencies, Rust worker, dashboard, database schema, credentials, account routing, and data volume are retained.

## Verification

- Five new subprocess regressions passed after reproducing failures on the old implementation. They cover concurrent HTTP bursts, mixed binary/text WebSocket delivery through the relay, terminal ordering, a stalled consumer alongside a healthy stream, closing, and cancellation.
- The isolated Linux test image passed 243 tests, including both native wire probes, routing and replay contracts, WebSocket adapters, process recovery, fallback, and terminal cancellation. The larger wire probe delivers 512 deltas and a completion on each of two HTTP and two WebSocket streams concurrently.
- Local focused checks passed 25 native HTTP tests and 183 account-health, compaction, owner, and continuation tests. Ruff checks and formatting and `ty` checks passed for the changed runtime and regression files.
- Real HTTP inference, two WebSocket turns using `previous_response_id`, and `/v1/responses/compact` passed through the candidate before cutover and against production after cutover.
- Production source hashes matched the staged hashes. The first post-verification request sample contained ten successful requests and no errors. The later sample contained 25 successes and one generic `interrupted` WebSocket response with no transport failure metadata. That sample had no `stream_incomplete`, consumer-backpressure, or owner-unavailable errors. This is a short observation window, not a claim that every future long chat will succeed.
- The changed OpenSpec capability and change pass strict validation. Repository-wide strict validation reports nine pre-existing failures in untouched capabilities: compatibility-tooling, database-backends, frontend-architecture, model-catalog-compat, query-caching, responses-api-compat, upstream-proxy-routing, usage-error-metrics, and usage-refresh-policy. No cloud CI or PR merge was claimed.

## Safeguards and cutover

Staging used isolated container filesystems with no production volume or account credentials. The production image was not changed in place. An intentionally unhealthy disposable deployment demonstrated automatic Swarm rollback, and an independent local supervisor demonstrated restoring the original production image on a disposable service.

A consistent SQLite backup was made under an explicit read transaction so active writes could not restart the backup indefinitely. The 6,506,639,360-byte snapshot passed `PRAGMA quick_check`; its SHA-256 is `e042e8985f0c64ef10aff5568cf143229c971e06f140b7a66f42623812012751`. The snapshot and encryption key are retained at `/var/lib/codex-lb/recovery-native-backpressure-20261110/`. Private application/container configuration snapshots are retained on the operator PC, outside Git.

Production uses a SQLite lifetime lock. The initial overlapping rollout was rejected while the old instance continued serving, and the supervisor verified recovery to the previous image. The completed cutover used the deployment's required stop-first order, with automatic Swarm rollback enabled and a detached Windows supervisor able to recover without model inference. Production readiness and inference were verified at `2026-11-10T09:36:11Z`, followed by a five-minute readiness observation and another inference probe.

Production is pinned to the immutable patched image, with Git auto-deploy disabled to prevent the unchanged `prod` branch from overwriting the fix. The original deployment branch was not moved or merged. Integrate this focused commit through the repository's normal review gates before re-enabling Git auto-deploy.

## Recovery

The independent supervisor and private state are retained at `C:\Users\Kapitantutan\.codex\deployment-recovery\native-stream-backpressure-20261110\`. It reads credentials from the existing Dokploy CLI configuration and the inference key from the environment. No credential is committed here.

To restore the previous image independently of Codex, run on the operator PC:

```powershell
& 'C:\Github\codex-lb\.venv\Scripts\python.exe' -u 'C:\Users\Kapitantutan\.codex\deployment-recovery\native-stream-backpressure-20261110\supervisor.py' --rollback-only
```

This changes the application to the retained original image, uses stop-first ordering, waits for readiness, checks real inference, and restores the original deployment metadata. It retains the live database and encryption configuration. Do not restore the database snapshot for an image-only rollback; that would discard writes made since the backup. Retain both image IDs while the hotfix remains active.
