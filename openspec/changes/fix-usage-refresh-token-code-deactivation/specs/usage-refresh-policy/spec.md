## MODIFIED Requirements

### Requirement: Usage refresh cools down repeated auth-like failures

Background usage refresh MUST apply a cooldown to accounts that repeatedly fail usage refresh with ambiguous `401` or `403` responses. Accounts in that cooldown window MUST be skipped until the cooldown expires or a later successful refresh clears it.

#### Scenario: Ambiguous usage 401 enters cooldown
- **WHEN** usage refresh receives a `401` that does not match a permanent account deactivation signal
- **THEN** the account is not deactivated immediately
- **AND** subsequent refresh cycles skip the account until the cooldown window expires

#### Scenario: Token-refresh-specific usage 401 retries refresh
- **WHEN** usage refresh receives a `401` with a token-refresh-specific code such as `refresh_token_expired`
- **THEN** the account is not marked `deactivated` from the usage response alone
- **AND** usage refresh attempts the token refresh-and-retry path before applying cooldown behavior

#### Scenario: Successful refresh clears cooldown
- **WHEN** a later usage refresh succeeds for an account that had been cooled down
- **THEN** the cooldown is cleared
- **AND** normal refresh cadence resumes

### Requirement: Usage refresh deactivates on clear deactivation signals

The system MUST deactivate accounts when usage refresh receives a permanent account deactivation signal. At minimum, `402`, `404`, account-level permanent error codes such as `account_deactivated`, `account_suspended`, and `account_deleted`, and `401` responses whose message explicitly indicates that the OpenAI account has been deactivated MUST be treated as deactivation signals.

#### Scenario: Usage 401 deactivation message deactivates the account
- **WHEN** usage refresh receives HTTP `401`
- **AND** the upstream message states that the OpenAI account has been deactivated
- **THEN** the account is marked `deactivated`
- **AND** later usage refresh cycles skip that account
