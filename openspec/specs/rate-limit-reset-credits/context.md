# Per-account early reset

The early rule is owned by each account. It has no global master setting. All accounts default off; enabling one account does not change another. The existing global five-minute fallback remains independent and may redeem even when an account has not opted into early reset or its weekly quota will refresh within 24 hours.

Example: an opted-in account with 0% weekly remaining, a reset coupon expiring in six days, and weekly refresh two days away qualifies. If weekly refresh is only 23 hours away, it waits. Exactly 24 hours qualifies at the final check.

The scheduler uses persisted weekly data only to find candidates. The serialized consume path refreshes usage and receives weekly evidence directly from that response, rechecks the opt-in, and validates the natural refresh and credit expiry deadlines before pinning. Missing weekly data does not fall back to an old exhausted row. A slow route lookup cannot bypass the final 24-hour check.

Both automatic modes share the existing account/UTC-expiry-date request identity. Automatic pins remain for eight days; manual pins retain 24-hour retention. This conservative policy intentionally suppresses additional automatic coupons sharing one account and expiry date. Ambiguous pinned outcomes are not automatically retried. Account status remains owned by the normal usage-refresh path; reset-credit polling failures do not change it.
