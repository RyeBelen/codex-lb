## 1. Dependency updates

- [ ] 1.1 Update the affected Rust direct constraints and transitive lock entries; verify Rust checks, native wire probes, and cargo-deny pass in cloud CI.
- [ ] 1.2 Update the four affected Python packages and runtime zlib; verify frozen dependency resolution, application tests, Docker build, and Trivy pass.

## 2. Release verification

- [ ] 2.1 Verify the current PR head passes all applicable cloud CI jobs and has no unresolved actionable review threads.
- [ ] 2.2 Rebuild the isolated Git application and verify source hashes and readiness with no production data attached.
- [ ] 2.3 Prepare the independent production Git deployment supervisor with recovery to the verified hotfix, source verification, and HTTP/continuation/compaction/readiness gates before enabling auto-deploy.
- [ ] 2.4 Record actual release evidence and validate and archive the completed change.
