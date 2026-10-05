# Decisions and rollout

The whitelist is separate from an API key's Assigned sources setting. Both must
permit a source. An empty source whitelist means all, including otherwise
authorized unauthenticated callers; one or more IDs excludes unauthenticated
callers. For example, selecting key A permits A but excludes B; clearing the
selection removes this additional restriction.

Store identifiers without a cascading key-deletion relationship so deleting the
last selected key cannot accidentally make a source public. Keep unavailable
IDs visible in the editor until an operator explicitly removes them. Reject
new nonexistent IDs while allowing an unchanged historical selection.

Use existing dashboard controls and CSS viewport sizing/overflow for dialogs.
No new dependencies or global dialog behavior change is needed.

Rollout: run the normal Alembic upgrade before the updated application serves
requests, then verify create/edit, catalog visibility, and selected/unselected
requests. Existing sources retain unrestricted access after migration. This
work prepares and verifies the migration against isolated local test databases;
production migration/deployment requires separate approval.
