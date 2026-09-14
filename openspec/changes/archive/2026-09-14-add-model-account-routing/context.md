# Model account routing

This policy controls which upstream subscription accounts may spend usage on a model. It is independent of the model catalog and API-key permissions. External model sources retain their own routing and permissions.

In Settings, expand Advanced and open Model account routing. Add the exact model ID, select the allowed accounts, and save. For example, create a rule for `gpt-6-astra`, press Select Pro accounts, adjust the selection, and save. Leave `gpt-5.6-sol` without a rule to keep its ordinary pool. The shortcut selects accounts whose current plan type is `pro`; it does not include Pro Lite or automatically select future accounts.

An absent policy permits normal routing. A stored policy with no grants blocks the model on the account pool. Deleting the last account does not remove that policy. To remove a restriction, edit its rule, choose All eligible accounts, and save.

Rules are evaluated after request model enforcement and existing alias normalization. Use canonical upstream model IDs. Whitespace and case are normalized for policy lookup; wildcard and model-family rules are not supported. Transcription uses `gpt-4o-transcribe` for policy checks while retaining its separate catalog behavior.

Selections and upstream submissions read committed policy without a process cache. This adds indexed database reads but lets later requests on existing connections observe edits. Work already submitted can finish. Pinned state never moves to an unlisted account. Limit warm-ups, quota-planner probes, and automation pings also check the model rule before sending. Background jobs retain their existing error reporting and settlement behavior.

Realtime attachment and frames use the API key's enforced model when present. Opaque Realtime call bodies do not currently provide a persisted model identity, so a call without a known model cannot use model-specific filtering. Existing API-key and account permissions still apply.

The additive migration creates no rules and leaves existing account and API-key data unchanged. A downgrade removes only the new policy tables. This change has been developed locally; deploying it and selecting production accounts are separate actions. Deployment should use the existing GitHub `prod` integration.
