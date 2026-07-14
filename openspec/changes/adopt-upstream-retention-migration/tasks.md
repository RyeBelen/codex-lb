## 1. Upstream adoption

- [x] 1.1 Merge upstream main and resolve overlapping runtime behavior toward upstream
- [x] 1.2 Remove the fork-only daily aggregate runtime and CLI

## 2. Migration compatibility

- [x] 2.1 Add fork revision remaps
- [x] 2.2 Import and verify legacy lifetime sums before dropping the retired table

## 3. Verification and rollout

- [x] 3.1 Rehearse against the production SQLite snapshot with integrity and drift checks
- [x] 3.2 Run retention, migration, conflict-focused tests, lint, and type checks
- [ ] 3.3 Commit, push main, and verify Railway migration and health

