# Change: Add general API-key model deny policy

## Why

API keys can currently restrict access only by enumerating every allowed
model. Operators also need a general way to deny a small set of models while
allowing present and future models by default.

## What Changes

- Add an optional `denied_models` API-key field beside `allowed_models`.
- Treat an empty allowlist as unrestricted and make deny rules take precedence.
- Reject contradictory allow/deny configuration and enforced denied models.
- Apply the policy to requests, model catalogs, and model-source selection.
- Add mutually exclusive Allowed models and Denied models checkbox selectors
  to the create and edit dialogs and summarize both policies in the key table.

## Impact

- Existing keys remain unrestricted unless they already have an allowlist.
- One nullable database column and its reversible migration are added.
- No model-specific permission fields or new dependencies are introduced.
