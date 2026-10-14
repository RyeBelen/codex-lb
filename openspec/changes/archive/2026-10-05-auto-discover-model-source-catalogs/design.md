# Design

Persist `auto_discover_models` independently of effective rows and `catalog_revision`, advanced atomically on operator updates. A guarded source-row update locks and checks the fetched revision before atomic model reconciliation. Network requests run outside sessions. Empty models enable automatic mode and preserve cache, nonempty models select manual mode, omitted models preserve both.

Reuse ModelRefreshScheduler lifecycle and leader gate. Its builder always enables the loop; a separate subscription-refresh flag retains `model_registry_enabled` behavior. Source refresh runs first with sequential bounded fetches and isolated failures.

Reuse forwarding URL/header/credential/session helpers. GET `/models` appended to normalized base URL, cap duration/body/model count, validate full JSON list and deterministically deduplicate IDs. Typed metadata allows supported advertised fields only; no remote operator controls. Explicit per-million/per-minute price units only; no inference from names. Preserve surviving IDs and disabled states.

Dashboard response exposes `autoDiscoverModels`. Configured input stays blank in automatic mode, discovered models stay visible, source protocol/access settings remain editable, and model metadata controls are disabled until manual IDs are entered. Preserve scrolling.
