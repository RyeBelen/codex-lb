# Change: Route by known account model capabilities

## Why

Plan-level model availability is not account-level evidence. When one account's
catalog refresh fails or a new account becomes selectable before refresh,
falling back to plan metadata can route a request to an account that never
advertised the requested model.

## What Changes

- Treat a successful or retained account catalog as the routing authority for
  that account even while coverage of the whole pool is incomplete.
- Exclude accounts without catalog evidence from catalog-known subscription
  models and service tiers until their catalog is fetched.
- Preserve the existing fallback for operator-mapped slugs that have never
  appeared in subscription discovery.
- Apply the same checks to fresh selection and HTTP bridge reuse.

## Impact

- A newly added or temporarily unknown account may wait for the next model
  refresh before receiving catalog-known requests.
- Client discovery keeps its existing bootstrap and retained-catalog behavior.
- No database or API schema changes are required.
