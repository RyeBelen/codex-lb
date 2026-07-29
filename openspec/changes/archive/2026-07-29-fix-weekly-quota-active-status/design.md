## Context

The deployed branch contains dashboard status derivation but omits the fork's focused weekly-quota fix. Production evidence showed six accounts with zero weekly remaining counted as active solely because `credits_has` was true while their recorded balance was zero. See `proposal.md` for motivation.

## Goals / Non-Goals

**Goals:**

- Reuse the fork's existing, tested quota derivation change.
- Keep proxy selection, persisted effective status, account summaries, and dashboard counts aligned.
- Preserve the exact deployed branch as the rollback point.

**Non-Goals:**

- No upstream contribution or pull request.
- No schema or data migration.
- No changes to how credit metadata is fetched or displayed.
- No manual edits to production account rows.

## Decisions

### Make weekly percentage authoritative

The shared quota helper will derive `quota_exceeded` whenever the effective weekly window is exhausted. Credit fields remain observable metadata but no longer override that usage state. This follows the existing fork commit instead of adding a dashboard-only count rule, because a UI-only rule would leave routing and status APIs inconsistent.

### Preserve distinct primary and secondary inference controls

The shared helper keeps separate inference controls for the short and long windows. Proxy state construction enables long-window inference for weekly rows while preserving existing monthly-window handling. This avoids broadening the production change beyond the requested weekly behavior.

### Port the focused fork commit onto the deployment lineage

The change is applied to the current deployed commit rather than promoting all of fork `main`. This keeps unrelated upstream/fork history out of the production rollout and preserves the reconnect-loop fix already deployed.

## Risks / Trade-offs

- [Credit-backed traffic could theoretically succeed after weekly usage reaches 100 percent] → Production evidence and the existing fork decision treat the weekly window as authoritative; regression tests lock this contract.
- [Porting an older fork commit onto the v1.22 deployment lineage can conflict] → Resolve only in the touched quota/status files and run focused plus broader tests.
- [Account counts can change during verification as usage refreshes] → Compare the UI to a same-time backend aggregate and verify no active summary has zero weekly remaining.

## Migration Plan

1. Port the fork's focused commit onto the current deployment branch.
2. Run OpenSpec, unit, integration, lint, and deterministic live-data checks.
3. Push an exact fork tag and update only the Dokploy compose image/build reference.
4. Verify health, logs, account counts, and reconnect-loop protections.
5. Roll back the compose reference to `dokploy-reconnect-loop-fix-844a2d35` if validation fails.
