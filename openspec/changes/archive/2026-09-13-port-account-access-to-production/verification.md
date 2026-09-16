# Production verification

Verified on 2026-09-13. The deployed code commit is `0f4e9743f86226daa7555d94d674daf9e0afbb1c`, based on production commit `afcba0132dbf26c2d7f7c9f0180df066dd37067c`.

## Local results

- Frontend: 1,248 tests passed across 155 files. The six account access editor tests also passed independently. Production build and lint passed.
- Backend application Ruff and type checks passed.
- Focused account access, session revocation, migrations, and existing Realtime integration: 66 passed.
- PostgreSQL account access, session, and migration coverage: 30 passed.
- Final Linux run on production's Python 3.14.7: 140 passed and one failed. The native Realtime connector test failed identically on unchanged production code because its mocked Python connector did not intercept the native transport.
- Windows unit run: 7,624 passed, 94 failed, 101 skipped, two collection errors. The baseline reproduced 89 failures and both collection errors. The five introduced failures were corrected and verified in the complete WebSocket cancellation file, 28 passed, and migration remap checks, four passed.
- Broad integration run: 564 passed, 18 failed, three skipped. The baseline reproduced 17 failures, including existing timeout and hang cases. The remaining reset-credit test stub was updated and the complete reset suite passed, 21 tests.
- Strict whole-repository OpenSpec validation initially reported 50 passing and nine failing specs. The unchanged baseline reported 49 passing and the same nine failures. This change validates strictly.

These results do not constitute an all-green repository suite. Baseline failures were kept separate from introduced regressions.

## Packaged and staging checks

The Linux image was built from a Git archive with `core.autocrlf=false`. Windows checkout line endings had made the first archive's entrypoint unusable; the corrected archive and server Git checkout both produced working Linux startup.

Local and server API checks passed startup, shared migration defaults, policy save/reload, invalid-update atomicity, revocation, and independent model-deny policy preservation. Existing Realtime attachment and frame revocation scenarios passed, including lease cleanup. A production endpoint request without a dashboard session returned the expected authentication error.

Staging rehearsals exercised a successful deployment and a deliberately failing startup followed by independent schema downgrade and prior-image recovery. The rehearsal also exposed drain response parsing and Dokploy stop response timeouts in the temporary deployment script. Both were corrected before the production attempt.

## Backup and rollback

The production SQLite database uses WAL. A chunked backup without a fixed snapshot timed out under continuous writes and left an empty file. A subsequent read snapshot backup completed and passed full integrity checking.

- Backup size: 5,146,005,504 bytes.
- SHA-256: `96b4821fb9dae41b1c2f45a549a7134bade5d27f1db8c957c44422c17573c462`.
- Contents: 43 accounts and 33 API keys.
- A copy was upgraded, modified, and downgraded. All 57 existing tables retained their row counts, the post-upgrade write survived, and full integrity and foreign-key checks passed.
- Upgrade took 0.213 seconds and downgrade took 0.158 seconds on that copy.

The backup, encryption key copy, and recovery evidence are retained in the production data volume under `account-access-rollout-20260913/`. No stale database backup was restored over live data.

## Deployment outcome

The first manually pinned deployment passed internal readiness, all 20 changed backend source hashes, shared defaults, and unchanged key-policy checks. A public readiness check returned 502 during startup. Automatic recovery downgraded the access schema and restored the previous image. Public inference was subsequently verified on the original service. A single immediate public check was insufficient for the routing transition; the verification was changed to wait for Docker health and bounded public-route readiness.

The final deployment used the existing GitHub integration. The tested commit was pushed directly to `prod`, with automatic deployment enabled. Dokploy deployment `Wr7yFiyND6X2UaOdu0r93` completed. The running image was:

`sha256:56e4ef1320c4d37ac64a7bf4d8f30360d58da0ebc8f8b2b7e0d82dec6c9fbc9c`

The running source matched all 20 changed backend file hashes. Both configured public domains returned readiness success, and an authenticated production Responses request reached `response.completed`. All 43 accounts remained shared, all 33 keys remained present, and the existing account assignment and model-policy fingerprint matched before and after deployment.

The service remains configured for GitHub branch `prod` with automatic deployment enabled. The Docker healthcheck now uses an executable `CMD` array. Updates use stop-first ordering and a 60-second stop grace period for the single SQLite application process.

All three temporary account-access applications and the older Astra production verification compose service were removed after verification. The production environment contains only its server application.
