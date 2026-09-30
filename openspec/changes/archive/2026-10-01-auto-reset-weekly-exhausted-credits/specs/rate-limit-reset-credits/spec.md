## ADDED Requirements

### Requirement: Optional weekly-empty automatic reset
The system SHALL expose default-off per-account preference `auto_redeem_reset_credits_when_weekly_exhausted`. When enabled it SHALL redeem the soonest available credit only when its expiry is in (now, now + seven days] and a fresh weekly quota sample has finite used percentage at least 100 with a known finite reset deadline at least 86400 seconds in the future. Weekly-only quota in the primary slot SHALL qualify; short-window, monthly, model-specific, rounded display, unknown or stale data SHALL NOT qualify. The scheduler SHALL use existing polling and redemption serialization, refresh weekly evidence inside the lock before pinning, recheck account opt-in and target eligibility, and skip inconclusive attempts without pinning. The existing global five-minute option and manual/v1 behavior SHALL remain independent of both account opt-in and the 24h guard. The new preference SHALL NOT be a global dashboard setting. The system SHALL recheck the weekly deadline immediately before pin/consume, including after credit fetch. Both enabled SHALL issue at most one action per tick and retain the last-minute fallback. Disabling polling SHALL prevent either automatic mode; newly enabling either automatic mode while polling is disabled SHALL be rejected, but unchanged persisted opt-ins SHALL remain savable.

#### Scenario: Weekly exhausted six days before expiry
- **GIVEN** the account opts in, a credit expires in six days, fresh weekly usage is 100 percent and its reset is more than 24h away
- **WHEN** the scheduler evaluates the account under the redeem lock
- **THEN** exactly one soonest-credit consume occurs through the existing helper

#### Scenario: Inconclusive or recovered weekly sample
- **WHEN** pre-consume refresh fails, omits weekly data, reports less than 100 percent used, or the weekly reset has elapsed
- **THEN** the early mode does not pin or consume a credit

#### Scenario: Legacy and early settings are independent
- **WHEN** only the old setting is enabled
- **THEN** redemption retains the existing five-minute behavior regardless of weekly exhaustion

#### Scenario: Opt-out or near natural refresh
- **WHEN** the account opts out before the locked guard or its fresh weekly refresh deadline is less than 24 hours away
- **THEN** the early mode does not pin or consume a credit

#### Scenario: Exact natural refresh boundary
- **WHEN** the fresh weekly refresh is exactly 86400 seconds away at final eligibility evaluation and all other early conditions hold
- **THEN** the early mode may consume one credit


### Requirement: Automatic pins cover the early eligibility period
Automatic case-sensitive `auto-reset-credit:` request pins SHALL remain readable and immune to opportunistic purge for eight days; other request pins SHALL retain their existing 24-hour lifetime. Both modes SHALL retain the same account/UTC-credit-expiry-date identity. Already-pinned automatic requests SHALL NOT repeat upstream consume or select another credit, including after an ambiguous outcome.

#### Scenario: Manual writes cannot purge a two-day-old automatic pin
- **WHEN** a manual redemption pins its request after an automatic pin is two days old
- **THEN** the automatic pin remains readable and suppresses another automatic consume

#### Scenario: Case-variant request uses manual retention
- **WHEN** a request id uses a case-variant prefix such as `AUTO-RESET-CREDIT:`
- **THEN** both pin reads and purges apply the ordinary 24-hour lifetime

## MODIFIED Requirements

### Requirement: Reset credit redemption is serialized and idempotent across replicas

Per-account redemption serialization MUST hold across all replicas and processes sharing one database. On PostgreSQL the system SHALL use `pg_advisory_xact_lock` keyed by the account id on the caller's session. On SQLite the system SHALL acquire a durable claim row via a single atomic conditional upsert (`INSERT ... ON CONFLICT(account_id) DO UPDATE ... WHERE expires_at < now`) with a 30-second lease, a bounded retry loop that surfaces a client-facing conflict on timeout, release on completion, and takeover of expired claims. While the redeem section runs, the claim holder SHALL renew its lease on a heartbeat cadence shorter than the lease (10 seconds) so a redemption that legitimately outlives one lease (e.g. slow upstream fetch/consume) is NOT taken over by a concurrent process; lease expiry without renewal remains the crash-recovery path. A claim-acquisition timeout SHALL surface in the caller surface's native error envelope: the dashboard error envelope on the dashboard consume endpoint and the `/v1/*` OpenAI error envelope (HTTP 409) on `POST /v1/reset-credit`. The system SHALL persist the `(account_id, redeem_request_id) -> credit_id` mapping in the shared database, committed inside the serialized section BEFORE the upstream consume call; a retry carrying the same `redeem_request_id`, served by ANY replica, MUST resolve to the originally selected `credit_id` and MUST NOT consume a different credit. Ordinary ledger rows SHALL be retained for 24 hours and automatic `auto-reset-credit:` namespace rows SHALL be retained for eight days (including after a failed consume, so a retry retargets the same credit), then purged opportunistically. Expired rows for an account SHALL be purged BEFORE a new pin is inserted, so that reusing a `redeem_request_id` after its prior row has aged past its applicable TTL durably re-pins the new attempt to its newly selected `credit_id` instead of silently discarding the new pin because an `ON CONFLICT DO NOTHING` insert collided with the soon-purged expired row. The pin lookup SHALL apply the same applicable TTL on read: a ledger row whose `created_at` is older than the TTL MUST be treated as absent (not returned as a durable pin) so a reused `redeem_request_id` is re-selected against the fresh fetch and re-pinned rather than forwarded for the stale expired `credit_id`; the read TTL and the purge TTL SHALL be the same duration. Both the dashboard consume endpoint and `POST /v1/reset-credit` SHALL redeem inside this cross-replica serialized section.

#### Scenario: Retry lands on a second replica and reuses the pinned credit
- **GIVEN** replica A redeemed the soonest credit for `redeem_request_id` R but the client never saw the response
- **WHEN** the client retries the consume with the same R and the request is served by replica B
- **THEN** replica B forwards the originally pinned `credit_id` to upstream
- **AND** no second credit is consumed for that account

#### Scenario: Two processes on one SQLite file redeem concurrently
- **GIVEN** two processes sharing one SQLite database each receive a consume request for the same account at nearly the same time
- **WHEN** the first process holds the durable redeem claim
- **THEN** the second process waits on (or conflicts out of) the claim instead of redeeming in parallel
- **AND** at most one upstream consume is sent per selected credit

#### Scenario: Claim holder crashes and the lease recovers
- **GIVEN** a process crashed while holding the redeem claim for an account
- **WHEN** a later consume request arrives after the claim lease has expired
- **THEN** the request takes over the expired claim and proceeds without operator intervention

#### Scenario: Slow redemption keeps its claim past the original lease
- **GIVEN** a process holds the redeem claim and its redeem section (upstream fetch/consume, usage refresh) runs longer than one 30-second lease
- **WHEN** a second process attempts to acquire the claim after the original lease would have expired
- **THEN** the heartbeat-renewed lease rejects the takeover and the second process keeps waiting (or conflicts out)
- **AND** at most one upstream consume is sent per selected credit

#### Scenario: Reused redeem_request_id after TTL re-pins the new credit
- **GIVEN** an account has a ledger row for `redeem_request_id` R pinned to credit C1 whose `created_at` is older than its applicable TTL
- **WHEN** a new redemption reuses R and selects a different credit C2
- **THEN** the expired row is purged before the new insert so the ledger persists `(R -> C2)`
- **AND** a same-R retry served by any replica retargets C2, not the discarded C1

#### Scenario: Expired pin is ignored on read
- **GIVEN** an account has a ledger row for `redeem_request_id` R whose `created_at` is older than its applicable TTL
- **WHEN** the pin lookup for `(account_id, R)` runs before any purge write
- **THEN** the lookup returns no durable pin (the expired row reads as absent)
- **AND** the redemption re-selects against the fresh fetch and re-pins the newly selected credit rather than forwarding the stale expired `credit_id`

#### Scenario: Claim contention on the v1 surface uses the OpenAI envelope
- **GIVEN** another process holds the redeem claim for the whole acquisition timeout
- **WHEN** a client calls `POST /v1/reset-credit` for that account
- **THEN** the endpoint returns 409 in the `/v1/*` OpenAI error envelope, not the dashboard envelope
