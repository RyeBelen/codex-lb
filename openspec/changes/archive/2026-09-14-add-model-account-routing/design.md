## Context

Production already intersects API-key assignments and account grants at selection and submission boundaries. Catalog eligibility expresses capability, not an operator's desired usage allocation.

## Goals / Non-Goals

Reserve exact model IDs for explicitly selected upstream accounts, with default unrestricted routing and no fallback outside a configured rule. Account plan is a selection shortcut, not a live predicate. External model-source permissions remain independent. This change does not deploy or enable a production rule automatically.

## Decisions

Store a model policy row and normalized account grant rows. A missing policy permits the normal pool; an existing policy with no grants denies the whole account pool for that model. Foreign keys remove account grants on deletion without removing the policy. Pending deletions are excluded from reads and eligibility. This avoids making deletion of the last account silently disable the restriction.

Use the existing account scope and pre-submission authorization functions with an optional effective model. Query committed policy using the same independent session, including on reused HTTP bridge/WebSocket submissions. Keep model filtering independent from discovered capabilities and from per-key model authorization. Already submitted requests can complete. Explicitly pinned owners fail rather than moving account-bound state to another account.

Apply the same model-only authorization to direct background senders for limit warm-ups, quota-planner probes, and automation pings. Transcription and Realtime can pass a policy model separately from the Responses catalog model to preserve their existing catalog behavior.

Expose authenticated dashboard list and per-model policy replacement endpoints. Validate IDs, normalize exact model IDs, and serialize updates to existing policies. A concurrent first creation can return a conflict without partial grants. The settings editor lists rules and has explicit save, unrestricted, empty selection, and read-only states. The Pro shortcut replaces the selected IDs with currently listed Pro accounts; future accounts need explicit selection.

## Risks / Trade-offs

Additional indexed policy queries add request-path database work. Share the already-open policy session and avoid process caches that could ignore revocation. Test retries, reused connections, empty rules, and account deletion. No model family wildcards or implicit aliases are introduced.

## Migration Plan

Add the two tables after the account-access revision, with no initial rules or changes to existing accounts and keys. Verify SQLite and the migration graph locally. Downgrade removes only the new routing policy tables. Follow the existing GitHub prod deployment workflow when deployment is requested.
