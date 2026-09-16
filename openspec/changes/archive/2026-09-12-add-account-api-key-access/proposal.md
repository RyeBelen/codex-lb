## Why

Assigning accounts to an API key limits that key but does not reserve those accounts. Operators need to reserve selected accounts without maintaining exclusions on every existing and future key.

## What Changes

- Add shared or restricted API-key access to accounts, with an explicit allowlist.
- Intersect account grants with existing key account scope for inference, retries, session reuse, and account-backed client reads.
- Add an authenticated dashboard editor and a backward-compatible database migration.
- Validate locally before any deployment.

## Capabilities

### New Capabilities
- `account-api-key-access`: Account access grants, management, and enforcement across client request paths.

### Modified Capabilities

## Impact

Account persistence and dashboard APIs, proxy account selection and connection reuse, account-backed usage reads, and the accounts dashboard. Existing accounts remain shared. Key account assignments retain their existing meaning.
