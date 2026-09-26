## ADDED Requirements

### Requirement: Dashboard operators can update upstream proxy pools

The dashboard MUST open a pool management modal when an operator activates a
pool name. The modal MUST let an authorized operator change the pool name,
active state, and selected endpoint members in one save. The API MUST reject
unknown pools, unknown endpoints, and duplicate endpoint IDs without changing
persisted state. It MUST preserve the weight, active state, and sort order of
retained members, append new members with defaults, remove deselected members,
and invalidate resolved upstream routes after a successful update.

#### Scenario: Change a pool and its members

- **GIVEN** a pool has an existing endpoint with non-default member settings
- **WHEN** an operator changes the name, deselects another endpoint, and adds a new endpoint
- **THEN** the pool name and membership are saved atomically
- **AND** the retained endpoint keeps its member settings
- **AND** subsequent route resolution uses the updated pool

### Requirement: Dashboard operators can delete unused upstream proxy pools

The pool modal MUST offer a confirmed Delete action. The API MUST reject
deletion while any account binding or the default route references the pool,
returning a dashboard validation error without changing either binding. On
successful deletion it MUST remove the pool and its members and invalidate
resolved upstream routes before responding.

#### Scenario: Bound pool cannot be deleted

- **GIVEN** an account binding or default route references a pool
- **WHEN** an operator confirms deletion
- **THEN** the API returns a `proxy_pool_in_use` validation error
- **AND** the pool and binding remain unchanged

#### Scenario: Delete an unbound pool

- **GIVEN** no account binding or default route references a pool
- **WHEN** an operator confirms deletion
- **THEN** the pool and its memberships are removed
- **AND** route resolution cannot select that pool

### Requirement: Endpoint actions live in an endpoint modal

The dashboard MUST open an endpoint modal when an operator activates an
endpoint name. Existing edit, test, and confirmed Delete actions MUST be
available within that modal. The summary row MUST NOT present those actions or
test output. The standalone Add pool member dialog and action MUST NOT appear;
pool membership MUST be managed in the pool modal.

#### Scenario: Test and edit an endpoint from its modal

- **WHEN** an operator opens an endpoint and tests it
- **THEN** the test result appears in that endpoint modal
- **AND** the same modal allows editing or confirmed deletion
