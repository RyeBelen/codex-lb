## ADDED Requirements

### Requirement: Realtime account access
Realtime sideband attachment and every subsequent client text or binary frame SHALL require committed account access for the call owner and API key. Revocation SHALL prevent the next frame from reaching upstream, close the relay, and release its account lease without penalizing account health. Call ownership SHALL remain bound to its original account and key.

#### Scenario: Revoke a live sideband
- **GIVEN** a key has a live Realtime sideband to account A
- **WHEN** its account grant is revoked and the client sends another frame
- **THEN** that frame is not sent upstream and the connection releases its lease

#### Scenario: Reattach after revocation
- **WHEN** a revoked key attempts to reattach to its existing call
- **THEN** the proxy rejects attachment before connecting upstream

### Requirement: Recoverable production rollout
Deployment SHALL preserve existing accounts as shared and the existing key model policy. Before stopping the serving process, the operator SHALL verify the exact candidate, a consistent database backup, the prior image, and a schema-compatible recovery procedure that runs independently of inference. Application processes SHALL NOT overlap on a shared SQLite database. Deployment completion SHALL require public readiness and authenticated inference verification.

#### Scenario: Candidate startup fails
- **WHEN** the candidate fails its bounded startup health checks
- **THEN** independent recovery restores the prior image with its compatible schema without waiting for model inference
