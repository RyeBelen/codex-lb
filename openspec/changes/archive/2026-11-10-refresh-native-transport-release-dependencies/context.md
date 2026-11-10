## Dependency validation

The initial cloud run on 39e9f27f9 passed application, database, migration, native wire, formatting, type, and packaging checks but failed the pre-existing dependency audits. The refresh in 88d3526d4 passes Rust dependency/license auditing, the Docker vulnerability gate, and Nix validation. Its unit run passed 7,923 tests and found one packaging assertion still naming the previous hyper/rustls pins; the follow-up updates those expected versions.

The Git-built staging image is `sha256:6dcc38ad70ef13797c9073b355ff9d8a531a4623cbcc3e644f16bbea881f31c6`. It became healthy with no production volume or account data. The four native-adapter source hashes match the committed hotfix after normalizing Windows CRLF to LF. Real HTTP inference, two WebSocket turns including `previous_response_id`, and `/v1/responses/compact` passed through the refreshed native helper to production.

## Recovery

The independent Git-release supervisor is stored outside the repository with existing deployment credentials kept in their protected configuration. Its recovery target is the currently serving fixed image `sha256:3f1addbd44c2f6194b19c12284986fa5954f1c4f3005f1bf12c45421821f1fd0`, rather than the older buggy release. Recovery from the refreshed Git image to that fixed image was exercised on the disposable service and reached healthy readiness at 2026-11-10T10:26:21Z. The disposable service had no production data mounts.

Production stayed pinned while the final current-head cloud gate ran. The verified tree was merged into prod and deployed through the independent supervisor. Git auto-deploy was enabled after source/binary checks, real inference/continuation/compaction probes, and 24 successful readiness observations. See release.json for the final receipt. Any rollback retains the live database; restoring the older SQLite backup would be a separate data-recovery operation.
