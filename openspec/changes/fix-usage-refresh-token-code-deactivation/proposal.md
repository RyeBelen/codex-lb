# Proposal: Fix usage refresh token-code deactivation

## Problem

Background usage refresh can receive an auth-like `401` from the usage endpoint with a token-refresh-specific error code such as `refresh_token_expired`. The current classifier treats every code in the global permanent failure set as a usage-level deactivation signal, so usage refresh can mark an otherwise valid account `deactivated` before attempting the existing refresh-and-retry flow.

## Change

- Restrict usage-refresh permanent deactivation code matching to account-level permanent signals.
- Keep `402`, `404`, and explicit deactivation messages as deactivation signals.
- Let ambiguous or token-refresh-specific `401` usage failures refresh the token and retry before entering cooldown.

## Impact

Accounts with stale access/session state should no longer be randomly marked deactivated by usage refresh. Truly deactivated/suspended/deleted accounts still fail closed.
