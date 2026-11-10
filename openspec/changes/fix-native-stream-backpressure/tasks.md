## 1. Native scheduling and classification

- [x] 1.1 Add deterministic regressions for burst delivery, stalled stream isolation, terminal ordering, and cancellation.
- [x] 1.2 Yield at both native queue producers, retaining bounded overflow and cancellation behavior.
- [x] 1.3 Classify local backpressure consistently across HTTP and WebSocket paths and retain safe WebSocket phase diagnostics.
- [x] 1.4 Verify relay account-health and continuity invariants with focused tests.

## 2. Verification and release

- [x] 2.1 Run focused regressions, lint, types, and strict OpenSpec validation; commit the scoped fix.
- [ ] 2.2 Build and verify an isolated immutable candidate against the exact production image, including native wire bursts and inference.
- [ ] 2.3 Preserve production data/configuration and verify independent health monitoring and rollback before rollout.
- [ ] 2.4 Roll out with automatic recovery armed and verify production readiness, inference, and error behavior.
- [ ] 2.5 Record evidence, sync normative specs and stable context, verify and archive the change, and commit final artifacts.

