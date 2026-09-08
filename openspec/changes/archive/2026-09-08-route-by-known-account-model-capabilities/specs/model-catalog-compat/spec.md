# Model catalog compatibility delta

## MODIFIED Requirements

### Requirement: Known account catalogs constrain pooled routing

The system MUST retain the union of successfully refreshed account model
catalogs for client discovery. For any catalog-known subscription model,
request selection MUST route a model or explicit non-default service tier only
to accounts whose current or retained last-known catalog advertised that
capability. This account-level evidence MUST be used even when another active
or selectable account has no catalog evidence. Requests that omit a tier or
use the omit-equivalent `auto` or `default` tiers MUST use model-only account
filtering, including when reusing an HTTP bridge session. Operator-mapped model
slugs that have never appeared in subscription catalog discovery MUST retain
the existing plan-level fallback.

A service tier imposed by an API key's enforced service tier is not an explicit
request for that tier. When the requested tier originates from API key
enforcement and the model's catalog does not advertise that tier at all, the
system MUST remove the tier from the account-routed request, MUST select
accounts and reuse HTTP bridge sessions using model-only filtering, MUST
reserve, settle, and log API-key usage at the effective default tier, and MUST
omit the unsupported tier from the upstream request. This account-catalog
fallback MUST NOT alter a request selected for an external model source, and an
unknown or account-catalog-absent model MUST retain the enforced tier. When the model's catalog
does advertise the tier, account-level tier filtering MUST continue to apply
regardless of the tier's origin. A tier supplied explicitly by the client MUST
continue to filter accounts even when it equals the enforced value or uses an
equivalent alias and the model does not advertise it. When an
unavailable service tier is what excluded every account, the selection error
MUST name that tier.

#### Scenario: Same-plan accounts expose different models

- **GIVEN** two active accounts share a plan
- **AND** only one account advertises a model
- **WHEN** request selection evaluates that model
- **THEN** the merged discovery catalog includes the model
- **AND** requests for that model select only the advertising account

#### Scenario: Same-plan accounts expose different Fast tiers

- **GIVEN** two active accounts advertise the same model
- **AND** only one advertises the priority service tier
- **WHEN** a request explicitly asks for priority
- **THEN** selection considers only the account that advertised priority

#### Scenario: Enforced tier does not exclude a model that never advertises it

- **GIVEN** an active account advertises a model at its default tier
- **AND** the model's catalog advertises no `priority` service tier
- **AND** an API key sets `enforced_service_tier` to `priority`
- **WHEN** account selection is requested for that model
- **THEN** the enforced tier is removed from the account-routed request
- **AND** API-key accounting, bridge compatibility, and upstream forwarding use the effective default tier
- **AND** the advertising account is selected

#### Scenario: Account-catalog fallback does not alter a model source

- **GIVEN** an API key enforces the `priority` service tier
- **AND** the selected model is routed through an external model source
- **WHEN** the subscription-account catalog does not advertise `priority` for that model
- **THEN** the source-routed request retains `priority`

#### Scenario: Explicitly requested unadvertised tier is still rejected

- **GIVEN** an active account advertises a model at its default tier
- **AND** the model's catalog advertises no `priority` service tier
- **WHEN** a client explicitly requests that model with `priority` or an equivalent `fast` alias
- **THEN** no account is selected

#### Scenario: Unavailable advertised tier names the tier in the error

- **GIVEN** a model's catalog advertises the `priority` service tier
- **AND** no active account carries `priority` for that model
- **WHEN** account selection is requested for that model with `priority`
- **THEN** no account is selected
- **AND** the selection error names the `priority` service tier

### Requirement: Unknown account catalogs fail closed for known capabilities

The system MUST distinguish an account catalog that successfully omitted a
capability from an account catalog that could not be fetched. An account with
neither a current nor retained last-known catalog MUST be excluded from
catalog-known subscription models and service tiers until catalog evidence is
available. A non-authoritative snapshot MAY still provide exact routing
evidence for the accounts it covers. Operator-mapped model slugs MUST NOT be
rejected solely because they are absent from subscription catalog discovery.

When there is no complete account coverage — including partial refreshes
after prior successful cycles and when every account is removed and live
capability state is cleared — the static bootstrap catalog MUST remain the
discovery and plan-gating floor. Clearing capability state MUST NOT publish an
authoritative-empty catalog that reports canonical models as absent;
otherwise, in the window after an account is added but before the next
scheduled refresh, `/v1/models` would report no models. Bootstrap discovery
alone MUST NOT qualify an account to receive a model.

Carrying a plan's catalog forward when its refresh does not complete MUST NOT
re-advertise a model that no currently-active account of that plan advertises,
per the last-known per-account catalogs. This drop invariant MUST hold
regardless of whether the previous snapshot was authoritative: the authoritative
distinction governs whether per-account routing is trusted, not whether a dead
model is dropped from discovery. When a carried-forward model has no per-account
provenance at all (an older or plan-only snapshot that never captured per-account
catalogs), the system MUST preserve it rather than drop it, degrading safe when a
model cannot be attributed to any account.

A retained account catalog MUST remain associated with the plan type that
produced it. If an active account changes plan type and its new catalog refresh
fails, the system MUST leave that account's catalog unknown rather than
re-labeling its old capabilities as support for the new plan. Any previously
advertised catalog slug explicitly suppressed because all its known advertisers
left the active set MUST still enter plan filtering and select no account,
whether or not it is part of the static bootstrap catalog; this is distinct from
an operator-mapped slug that has no catalog evidence at all.

#### Scenario: Catalog fetch partially fails after restart

- **GIVEN** there is no previous registry snapshot
- **AND** one active account catalog refresh succeeds while another fails
- **WHEN** selection evaluates a model or service tier
- **THEN** the partial index is non-authoritative
- **AND** the successful account's catalog is used as exact routing evidence
- **AND** the failed account is excluded from catalog-known capabilities

#### Scenario: No active accounts fall back to the bootstrap floor

- **GIVEN** live capability state is cleared because no active accounts remain
- **WHEN** an account is added before the next scheduled refresh completes
- **THEN** canonical bootstrap models remain discoverable via `/v1/models`
- **AND** those models remain plan-gated by the bootstrap catalog
- **AND** no account is selected for them without catalog evidence

#### Scenario: Failed refresh has last-known account data

- **GIVEN** every active account had a successful earlier catalog
- **AND** one account fails a later refresh
- **WHEN** that account remains active
- **THEN** its last-known capability data is retained
- **AND** the complete snapshot remains authoritative

#### Scenario: Successful empty catalog withdraws stale capabilities

- **GIVEN** an active account previously advertised a model
- **AND** its later catalog refresh succeeds with an empty model list
- **WHEN** the next registry snapshot is built
- **THEN** the empty catalog is treated as successful account coverage
- **AND** the previously advertised model leaves discovery and exact routing

#### Scenario: Metadata-only account model stays unroutable during partial refresh

- **GIVEN** an account catalog contains a model omitted from the plan discovery catalog
- **AND** a later refresh retains that account's stale catalog
- **WHEN** the next registry snapshot is built
- **THEN** the metadata-only model does not enter model, plan, account, or service-tier routing indexes

#### Scenario: Fresh metadata-only model stays out of routing indexes

- **GIVEN** a refreshed account catalog contains a model omitted from the merged discovery catalog
- **WHEN** the registry builds account and service-tier routing indexes
- **THEN** the metadata-only model does not enter either routing index

#### Scenario: Selectable account set is newer than registry coverage

- **GIVEN** an authoritative registry snapshot covers the previously selectable accounts
- **AND** a newly imported or reactivated account becomes selectable before the next catalog refresh
- **WHEN** request selection evaluates model or service-tier support
- **THEN** the new account is excluded from catalog-known capabilities
- **AND** covered accounts continue to use their exact catalog evidence

#### Scenario: Bridge owner is newer than registry coverage

- **GIVEN** an HTTP bridge session belongs to a selectable account absent from the registry snapshot
- **WHEN** a compatible follow-up evaluates model or service-tier support
- **THEN** the bridge owner is not reused for a catalog-known capability

#### Scenario: Failed refresh follows an account plan-type change

- **GIVEN** an account previously advertised a catalog while on one plan type
- **AND** the active account record now has a different plan type
- **AND** its catalog refresh fails in that cycle
- **WHEN** the next registry snapshot is built
- **THEN** the prior catalog is not retained for that account
- **AND** the account remains unknown until a catalog for its current plan is fetched

#### Scenario: Account is paused or removed

- **GIVEN** an account has retained catalog capabilities
- **WHEN** it is no longer in the active account set
- **THEN** its capabilities no longer contribute to discovery or routing

#### Scenario: Removed account is the sole advertiser within a stale plan

- **GIVEN** two accounts share a plan and only one advertised a given model
- **AND** the plan's refresh does not complete this cycle, so its catalog is carried forward
- **AND** the sole advertiser is no longer in the active account set
- **AND** the other account of that plan remains active
- **WHEN** the stale plan's retained catalog is merged into discovery
- **THEN** the model advertised only by the removed account leaves discovery
- **AND** the models still advertised by the remaining active account are retained

#### Scenario: Sole advertiser removed under a non-authoritative previous snapshot

- **GIVEN** a first refresh recorded a model advertised by one account of a plan
- **AND** a same-plan account had no catalog, so the snapshot is non-authoritative
- **WHEN** that sole advertiser is removed while another same-plan account stays active
- **AND** the plan's refresh does not complete in a later cycle
- **THEN** the model advertised only by the removed account still leaves discovery

#### Scenario: Removed catalog model stays suppressed across repeated partial refreshes

- **GIVEN** a snapshot suppressed a previously advertised catalog model because every last-known advertiser left the active account set
- **WHEN** later refresh cycles remain non-authoritative and still do not produce fresh active evidence for that model
- **THEN** the model stays absent from discovery and plan gating across those repeated partial refreshes

#### Scenario: Suppressed catalog model cannot select an account

- **GIVEN** a snapshot explicitly suppresses a previously advertised model because no active account advertises it
- **WHEN** account selection receives a request for that model
- **THEN** the selector rejects every account for that model
- **AND** it does not treat the known suppressed slug as an operator-mapped unknown

#### Scenario: First complete catalog suppresses omitted bootstrap model

- **GIVEN** there is no previous registry snapshot
- **AND** a bootstrap model slug is known to the proxy
- **WHEN** the first authoritative account-catalog refresh omits that model
- **THEN** the registry marks the omitted bootstrap slug as suppressed
- **AND** account selection does not treat that known slug as an operator-mapped unknown

#### Scenario: Fresh active evidence clears catalog suppression

- **GIVEN** a catalog model was previously suppressed after its last-known advertisers left the active account set
- **WHEN** a later refresh records that an active account advertises that model again
- **THEN** the suppression is cleared
- **AND** the model returns to discovery and plan gating from live registry data

#### Scenario: Never-known operator mapping remains distinct from suppression

- **GIVEN** an operator-mapped slug has never appeared in an account catalog
- **WHEN** an authoritative catalog snapshot does not contain that slug
- **THEN** the registry does not mark the slug as suppressed
- **AND** the existing operator-mapped unknown fallback remains available

#### Scenario: Carried-forward model has unknown per-account provenance

- **GIVEN** a plan-only snapshot carried a model with no per-account provenance
- **WHEN** the plan is stale in a later refresh that knows the active account set
- **THEN** the model is preserved in discovery rather than dropped
