## 1. Specification

- [x] Define allowlist, denylist, precedence, validation, and dashboard behavior.

## 2. Backend

- [x] Persist and expose nullable API-key denied-model lists.
- [x] Enforce deny-wins access across requests, catalogs, and model sources.
- [x] Reject overlapping allow/deny lists and denied enforced models.

## 3. Dashboard

- [x] Add mutually exclusive Allowed models and Denied models checkbox selectors.
- [x] Show allow and deny policy summaries in the API-key table.

## 4. Verification

- [x] Cover migration, service validation, request policy, catalogs, source routing, schemas, and dialogs.
- [x] Run focused backend/frontend checks and strict OpenSpec validation.
