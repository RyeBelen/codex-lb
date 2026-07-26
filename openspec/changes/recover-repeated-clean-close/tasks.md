- [x] Add bounded clean-close replay settings with safe defaults.
- [x] Allow one additional clean-close replay only before visible output.
- [x] Add jitter and dedicated retry diagnostics.
- [x] Add regression coverage for the second replay and retry cap.
- [x] Restart the upstream reader when pre-response recovery is initiated by the downstream stream task.
- [x] Add regression coverage for old-reader cancellation and replacement-reader ownership.
- [x] Keep the shared session live across the cancelled reader's socket-generation finalizer.
- [x] Add regression coverage for concurrent pruning during reader handoff.
- [x] Move the default pre-response recovery threshold ahead of the client timeout boundary.
- [x] Bound anchored stuck-gate grace and evaluate staleness from upstream activity/response creation.
- [x] Emit stuck-watchdog skip diagnostics with pending-state verdict inputs.
- [x] Add a forward-only repair for databases stamped before request-usage rollups were connected to the merge head.
- [x] Validate the OpenSpec change and run the focused and full test suites.
- [x] Build and deploy the validated image, then verify production health and logs.
- [x] Count `missing_response_created_timeout` as an eligible hard-affinity
  retry-circuit failure without changing soft-affinity or account-health
  behavior.
- [x] Add regression coverage for the production sequence from
  `stream_incomplete` through the missing-created watchdog and the suppressed
  follow-up replay.
- [x] Repair the stacked branch's stuck-watchdog diagnostic and retry-circuit
  test fixtures uncovered by the full HTTP bridge suite.
- [x] Re-run strict OpenSpec validation and the focused HTTP bridge, durable
  coordinator, migration, lint, and type-check suites.
