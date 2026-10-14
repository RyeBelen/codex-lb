# Model Source Routing — Context

## Purpose

Capability-based routing and accounting for OpenAI-compatible model sources,
including field-preserving embeddings forwarding.

This capability keeps source selection separate from subscription-account
routing: embeddings traffic is served only by sources that declare the
embeddings capability, while Responses/chat/audio continue to use their own
capability gates. Field presence (including explicit nulls) is preserved on
embeddings forwards so compatible sources see the same payload shape the
client sent.

## Source API-key access

Model Source create/edit offers an Allowed API keys selection. No selected keys
means available to all otherwise permitted callers. Selecting key A permits A
and excludes key B and unauthenticated callers. A key must also satisfy its
existing Assigned sources and model restrictions. Global API-key authentication
must be enabled for the application to identify bearer keys.

Source whitelists retain unavailable/deleted key IDs until an operator explicitly
removes them, so deleting the last selected key cannot accidentally make the
source public. The editor shows those IDs for removal. New nonexistent IDs are
rejected. Omitted source updates preserve the saved whitelist. Regenerating a
key retains its ID and therefore its source access.

The nullable JSON Text column defaults existing sources to unrestricted access.
A shared predicate filters model discovery and all capability source candidates.
Matching candidates are scanned in memory; indexed grants are the upgrade path
if source catalogs become large. Invalid stored whitelist data fails closed.

Run the standard Alembic upgrade before serving the updated app, then verify
selected/unselected model discovery and requests. Downgrading drops whitelist
configuration, and older code does not enforce it: review access consequences
and preserve configuration before a separately authorized production rollback.
The implementation and migration were verified against isolated local test data;
production deployment and database changes are separate operations.

The create/edit dialogs use viewport-bound height and vertical overflow so even
a short mobile viewport can reach the submit controls.


# Automatic Model Source catalog discovery

## Behavior
Leave configured model IDs blank to use provider discovery. The source remains automatic even after discovered models exist. Polling runs immediately at scheduler startup and five minutes after each completed pass. A newly saved source can wait for the next pass. Nonempty IDs choose manual mode, which never polls. Clearing a manual list retains effective rows until a successful provider response.

Examples: `https://api.example.com/v1` is queried at `https://api.example.com/v1/models`. A catalog containing only `{"data":[{"id":"local-coder"}]}` supplies a model ID, existing streaming/context defaults, and unknown pricing; no features are inferred from the name. `{"data":[]}` is authoritative and clears the effective automatic cache.

## Supported metadata
Typed advertised fields may appear at model top level, in `metadata`, or in `capabilities` (top level wins, followed by metadata, then capabilities). Supported fields: `display_name` (`name` alias), `description`, `context_window` (`context_length` / `max_context_window` aliases), `max_output_tokens`, `supports_streaming`, `supports_tools` (`supports_parallel_tool_calls` alias), `supports_vision` (`supports_images` alias), `input_modalities`, `supports_reasoning`, `supported_reasoning_levels` (strings or effort/description objects), `default_reasoning_level`, `supports_reasoning_summaries`, `supports_search_tool` and `experimental_supported_tools`. Reasoning levels imply support only if the provider did not explicitly advertise its reasoning flag. Image modality implies vision only if no explicit vision flag is supplied.

Rates `input_per_1m`, `cached_input_per_1m`, `output_per_1m`, `audio_per_minute` are accepted directly or under `pricing`, with direct explicit rates taking precedence. Their units are dollars per million tokens or per audio minute. Ambiguous vendor price units are not converted. Standard `object`, `created`, and `owned_by` fields are retained. Unknown fields and remote internal/operator configuration are ignored, including `source_id`, credentials and `source_request_overrides`. Source-level chat/Responses/audio/embedding protocols remain operator settings.

Known fields use strict types and size/value limits. A malformed catalog fails as a whole; duplicates use the first occurrence and are returned in ID order. Responses are capped at 4 MiB, 10,000 models, and the smaller of the source timeout or 30 seconds. Fetches are sequential; a large number of slow sources can lengthen a pass, so bounded concurrency is deferred until warranted. Failed network/auth/validation/write operations preserve the last successful cache. Only type names and source IDs are logged for failures; remote bodies and exception text are not logged.

## Persistence and races
The migration adds automatic ownership and an operator configuration revision. Historical empty sources become automatic; nonempty sources remain manual. Each operator update atomically advances the revision. Discovery first checks/locks the unchanged automatic enabled source row, then reconciles the catalog in the same write transaction. Network work runs outside sessions. Surviving models retain IDs and disabled flags. Manual edits, configuration changes, disable/re-enable and deletion during fetch invalidate that result. Shutdown/lease-loss cancellation propagates through the existing owned scheduler and HTTP/session contexts.

## Dashboard
Automatic sources keep configured IDs blank while showing cached discovered models. The visible source list polls the dashboard cache every 30 seconds only while at least one enabled automatic source exists; background polling is disabled. This does not add provider fetches. Per-model context/pricing/capability/reasoning controls reflect the first effective model and are disabled while automatic; source protocol toggles and API-key whitelist stay editable. Entering IDs enables manual metadata controls. Whitelists and existing API-key source/model restrictions still apply to effective catalogs and every forwarding route.

## Rollout
No production execution is included in this local implementation. For an authorized release, use normal `codex-lb-db upgrade head` then `codex-lb-db check` before starting the updated application. Review historical empty sources: enabled empty sources begin polling their configured providers after migration/startup, independently of subscription registry settings. Preserve the encrypted credential environment through normal deployment. Verify startup discovery, automatic mode after refresh, selected-key access, and the next five-minute pass using the operator's environment. Do not use migration downgrade as a production rollback after discovered rows are populated: restoring the old schema removes ownership and treats cached rows as manual; restarting the old app also stops periodic source discovery. No live provider calls or actual credentials were used for local verification.
