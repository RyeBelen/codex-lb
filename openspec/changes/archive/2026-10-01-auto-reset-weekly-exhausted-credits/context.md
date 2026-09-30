# Per-account early reset

The early rule is owned by each account. It has no global master setting. All accounts default off; enabling one account does not change another. The existing global five-minute fallback remains independent and may redeem even when an account has not opted into early reset or its weekly quota will refresh within 24 hours.

Example: an opted-in account with 0% weekly remaining, a reset coupon expiring in six days, and weekly refresh two days away qualifies. If weekly refresh is only 23 hours away, it waits. Exactly 24 hours qualifies at the final check.

The scheduler uses persisted weekly data only to find candidates. The serialized consume path refreshes usage and receives weekly evidence directly from that response, rechecks the opt-in, and validates the natural refresh and credit expiry deadlines before pinning. Missing weekly data does not fall back to an old exhausted row. A slow route lookup cannot bypass the final 24-hour check.

Both automatic modes share the existing account/UTC-expiry-date request identity. Automatic pins remain for eight days; manual pins retain 24-hour retention. This conservative policy intentionally suppresses additional automatic coupons sharing one account and expiry date. Ambiguous pinned outcomes are not automatically retried. Account status remains owned by the normal usage-refresh path; reset-credit polling failures do not change it.

Mock UI captures: `docs/screenshots/account-weekly-empty-before.jpg` and `docs/screenshots/account-weekly-empty-after.jpg`. The before view is the same mock scene with the new row removed, not a historical build. All verification used local temporary databases and mocked upstream; no live redemption or deployment occurred.

## Verification completed

- Scheduler/shared redemption/updater and early-reset integration: 256 tests passed. Account/API/repository/v1 compatibility: 100 passed. Ledger/replica safety: 21 passed. Final account SQL concurrency guard regressions: 4 passed.
- Final affected frontend suites: 124 tests across five files passed; earlier targeted account controls, i18n and two screenshot scenarios also passed. Python and TypeScript type checks, changed-file Ruff/ESLint and diff whitespace checks passed.
- Isolated migration upgrade/check reported `migration_policy=ok` and `schema_drift=none`; single-head, downgrade/upgrade and default-false backfill checks passed.
- Strict change validation and all 60 main specifications passed. Delta requirements were compared with synced main specs before archive.
- Final review fixed polling-disabled enable races with a guarded atomic SQL update, made older account payloads default false, and aligned case-sensitive automatic pin retention on read and purge. Regression assertions cover each.
- Limitations: focused suites, not a full repository test run; upstream mocked and migrations isolated. A pre-existing MSW unhandled-request warning remained while frontend tests passed. The before screenshot is a mock reconstruction. Changes are local and uncommitted; no production migration, live account mutation or redemption.
