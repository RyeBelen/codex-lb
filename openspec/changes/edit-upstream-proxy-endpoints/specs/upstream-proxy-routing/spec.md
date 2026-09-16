## ADDED Requirements

### Requirement: Dashboard operators can edit upstream proxy endpoints

The dashboard SHALL let an authorized operator update an existing upstream
proxy endpoint's name, scheme, host, port, username, active state, and
password without replacing the endpoint or its pool memberships. The API MUST
apply the same scheme and credential validation used when creating an
endpoint, MUST NOT return the stored password, and MUST preserve the existing
encrypted password when an edit omits a replacement password. Clearing the
username MUST clear the stored password. A successful update MUST invalidate
resolved upstream routes before returning.

#### Scenario: Edit an endpoint without replacing its password

- **GIVEN** an HTTPS proxy endpoint has stored credentials and belongs to a pool
- **WHEN** an authorized operator changes its host and leaves the password blank
- **THEN** the existing endpoint and pool membership remain in place
- **AND** the host is updated while the stored password is preserved
- **AND** the response does not expose the password
- **AND** subsequent route resolution uses the updated endpoint

#### Scenario: Clear endpoint credentials

- **GIVEN** a proxy endpoint has stored credentials
- **WHEN** an authorized operator clears its username
- **THEN** the endpoint username and stored password are cleared

#### Scenario: Invalid edited credentials are rejected

- **WHEN** an operator edits a plaintext proxy endpoint to carry credentials
- **THEN** the API returns a dashboard validation error
- **AND** the persisted endpoint remains unchanged

### Requirement: Dashboard operators can delete unused upstream proxy endpoints

The dashboard SHALL expose a confirmed destructive action for deleting an
upstream proxy endpoint. The API MUST reject deletion while the endpoint is a
member of any proxy pool, MUST leave the endpoint and memberships unchanged on
rejection, and MUST invalidate resolved upstream routes after a successful
deletion.

#### Scenario: Delete an unused endpoint

- **GIVEN** an upstream proxy endpoint is not a member of any pool
- **WHEN** an authorized operator confirms its deletion
- **THEN** the endpoint is removed
- **AND** subsequent route resolution cannot select it

#### Scenario: Reject deletion of an endpoint used by a pool

- **GIVEN** an upstream proxy endpoint is a member of a pool
- **WHEN** an authorized operator confirms its deletion
- **THEN** the API returns a dashboard validation error
- **AND** the endpoint and pool membership remain unchanged
