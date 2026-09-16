# Account access

Use Accounts > API key access to reserve an upstream account for selected client API keys. Shared is the default for existing and newly imported accounts. Restricted with no selected keys blocks all client inference, including requests without a key when proxy authentication is optional. Switch back to Shared and save to remove the restriction.

An API key's Assigned accounts setting and an account's Allowed API keys setting answer different questions. The first limits which accounts a key may use. The second reserves an account for particular keys. Effective access is their intersection. For example, reserving account A for key X does not prevent X from using shared account B. Assigning X only to B prevents X from using A even if A grants it access.

The database stores the restricted flag on the account and grants in `account_api_key_grants`. Existing `api_key_accounts` rows remain independent. Grant updates replace the policy in one transaction, validate all referenced keys, and preserve the previous policy when validation fails. Deleting the last granted key leaves the account restricted with an empty list. Regenerating a key preserves its stable ID and grants.

The proxy queries committed account policy when selecting accounts and before sending requests, including retries and reused HTTP bridge or WebSocket connections. Already submitted requests may finish after revocation. Account-bound files and previous-response owners fail when forbidden, without moving their state to a different account. Access denial does not penalize account health. Client account-pool usage, aggregate upstream quota, reset credits, and warm-up targets use the same account restrictions. Dashboard management and background maintenance keep their existing authority.

These queries add database work to selection and request submission. Grant lookups use account and key indexes, and concurrent operations use separate sessions. The initial WebSocket reader starts after authorization so database latency does not consume its upstream idle timeout before the first send.

The migration initializes all existing accounts as shared. Downgrading removes account restrictions and grants, so a downgrade is a rollback to shared access. Account records and existing per-key assignments survive the migration round trip. Deployment requires the existing repository validation and release gates.
