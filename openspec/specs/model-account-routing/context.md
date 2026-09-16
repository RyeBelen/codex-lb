# Model account reservations

This policy reserves upstream subscription accounts for particular models to protect their usage. It is independent of the model catalog and API-key permissions. External model sources retain their own routing and permissions.

In Settings, expand Advanced and open Model account routing. Add the exact model ID, select accounts to reserve, and save. For example, reserve three Pro accounts for `gpt-6-astra`. Those accounts then serve only Astra. Astra can also use unreserved eligible accounts, while `gpt-5.6-sol` cannot use the three reserved accounts. An account assigned to multiple model rules can serve any of those models.

Select Pro accounts selects the currently listed accounts whose plan type is exactly `pro`. It excludes Pro Lite. New accounts remain unreserved and eligible under ordinary routing until explicitly reserved.

An empty rule reserves no accounts and does not block its model. To release a reservation, edit the rule, choose Remove reservation, and save. An account remains reserved if another model rule still assigns it. Deleting the last selected account does not block that model from using unreserved accounts.

Rules use exact canonical model IDs after request model enforcement and existing alias normalization. Whitespace and case are normalized; wildcard and model-family rules are not supported. Transcription checks `gpt-4o-transcribe` while retaining its separate catalog behavior. API-key scope, account grants, model capability, health, and quotas still apply.

Selection and upstream submission read committed reservations without a process cache. Later requests on reused connections observe edits. Work already submitted can finish and settle normally. Pinned state never moves between accounts to evade a reservation. Limit warm-ups, quota-planner probes, and automation pings also check reservations before inference.

Realtime creation, attachment, and frames use the API key's enforced model when present. An unknown-model Realtime call excludes reserved accounts because its model cannot be established. Model-less file operations retain their existing authorization and account ownership.

Existing saved account selections become reservations without a schema migration or account-ID rewrite. The API's existing `restricted` field enables the reservation row; it does not limit the model to the selected accounts. Deployment uses the existing GitHub `prod` integration.
