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
