## Why

Restoring the native-stream hotfix to the production Git branch requires passing the fork's previously disabled CI workflow. Its dependency audits reject existing Rust, Python, and runtime zlib versions. The transport regressions and application tests pass independently of those audit failures.

## What Changes

- Update only the dependencies reported by the Rust and Docker audit gates to compatible fixed versions.
- Replace hyper's transitive unmaintained pin-utils dependency through the compatible hyper 1.9 release.
- Upgrade the runtime image's existing zlib package through Debian's security repository.
- Rebuild an isolated Git candidate, rerun the complete cloud merge gate, and preserve the deployed immutable hotfix as the recovery image.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. These dependency updates preserve the existing outbound HTTP/WebSocket contracts, native queue behavior, configuration, and database schema. This change uses `skip_specs: true` rather than adding an artificial requirement.

## Impact

Cargo version constraints and lockfile, Python lockfile, and the Docker runtime package upgrade list. No application source changes, new settings, account ownership changes, or migrations.
