## Context

The operator clarified that selected accounts are reserved for Astra, while Astra can also use other eligible accounts. The deployed model-to-account allowlist implements the wrong direction.

## Goals / Non-Goals

Reserve selected accounts for their assigned models. Preserve ordinary routing for unreserved accounts and all other permissions, capabilities, health, and quotas. Do not limit a model to its reserved accounts. Do not change account assignments or add a database migration.

## Decisions

Reuse model policy and grant rows as account reservations. An account with grants can serve only the exact models assigned to it. An account without grants remains available to any otherwise eligible model. Multiple model assignments permit their union. Empty reservation rows reserve no accounts and do not block a model. Removing a rule releases its accounts unless another rule still reserves them.

Apply the inverse filter through the existing committed scope checks at selection and submission, including background inference. Preserve model-less file operations. Realtime inference with an unknown model excludes reserved accounts because it cannot establish permission to spend their usage.

Update dashboard labels to say accounts are reserved for a model and that the model may use other eligible accounts. Previously saved selections take effect as reservations without rewriting their account IDs.

## Risks / Trade-offs

This intentionally changes the behavior of existing model rules to match the operator's request. The production Astra rule already contains the intended three account IDs. Validate both directions, retries, connection reuse, account/key scope, unknown-model inference, removal, multiple model assignments, and background sends before pushing.

## Migration Plan

No schema migration. Test locally, commit, and push through the existing GitHub `prod` deployment. Reuse the verified same-day database backup. Verify the deployed code, the three saved grants, routing eligibility, readiness, and authenticated inference. Reverting this correction restores the previous direction without changing stored rules.
