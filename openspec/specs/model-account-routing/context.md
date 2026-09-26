# Model account reservations

This policy reserves upstream subscription accounts for particular models to protect their usage. It is independent of the model catalog and API-key permissions. External model sources retain their own routing and permissions.

In Accounts, open an account and use Allowed models beside API key access. The checkbox list comes from that account's resolved subscription-model catalog. Select the exact models the account may serve and save. For example, selecting `gpt-6-astra` and `gpt-6-sol` means the account serves Astra and Sol but no other model. Those models can still use other unreserved eligible accounts.

No selected models means the account is unreserved and remains eligible for every model it supports. A selected model that later disappears from the resolved catalog remains visible as unavailable so the restriction can be removed. If no resolved or retained catalog exists for the account, the editor keeps saved selections editable and offers known public subscription models as provisional choices. It explains that support for this account is unverified until its catalog refreshes. The operator can clear all selections even when no models are currently known; this intentionally returns the account to unrestricted routing for whatever it supports after recovery. Unknown new IDs are rejected.

To release every reservation on an account, clear all checkboxes and save. Deleting the last selected account does not block a model from using unreserved accounts. The existing model-oriented backend API remains available for compatible clients, but the dashboard has one account-oriented editor.

Rules use exact canonical model IDs after request model enforcement and existing alias normalization. Whitespace and case are normalized; wildcard and model-family rules are not supported. Transcription checks `gpt-4o-transcribe` while retaining its separate catalog behavior. API-key scope, account grants, model capability, health, and quotas still apply.

Selection and upstream submission read committed reservations without a process cache. Later requests on reused connections observe edits. Work already submitted can finish and settle normally. Pinned state never moves between accounts to evade a reservation. Limit warm-ups, quota-planner probes, and automation pings also check reservations before inference.

Realtime creation, attachment, and frames use the API key's enforced model when present. An unknown-model Realtime call excludes reserved accounts because its model cannot be established. Model-less file operations retain their existing authorization and account ownership.

Existing saved account selections appear as allowed-model checkboxes without a schema migration or account-ID rewrite. The compatibility API's `restricted` field enables the reservation row; it does not limit the model to the selected accounts. Deployment uses the existing GitHub `prod` integration.
