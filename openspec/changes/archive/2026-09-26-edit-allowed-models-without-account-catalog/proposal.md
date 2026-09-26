## Why

When an account reaches its usage limit, its resolved model catalog can become unavailable. The account detail then hides Allowed models editing even though the saved routing policy is still available and may need changing.

## What Changes

- Keep the Allowed models form available when the account catalog is missing.
- Offer stored selections and known public subscription models as provisional choices, with account support marked unverified.
- Allow the API to save those choices while rejecting unknown model IDs and preserving read-only access.

## Impact

- Account Allowed models API, editor, focused tests, and model-account-routing spec/context.
- No migration or new dependency.
