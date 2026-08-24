# api-key-verbose-capture Specification

## Purpose

Provide an explicitly armed, bounded way for administrators to inspect request inputs for one API key without enabling broad or permanent payload logging.

## Requirements

### Requirement: Administrators can arm bounded verbose capture

The system SHALL let an administrator arm an existing API key to capture between 1 and 100 eligible requests. The dashboard API and API-key detail view MUST expose the number of capture slots remaining. Arming an already active capture SHALL replace its remaining budget with the newly requested count.

#### Scenario: Arm a key with the default dashboard count

- **WHEN** an administrator arms an API key for 10 requests
- **THEN** the API key reports 10 verbose capture slots remaining

#### Scenario: Replace an active budget

- **WHEN** a key has 4 capture slots remaining and an administrator arms it for 20 requests
- **THEN** the key reports 20 capture slots remaining

#### Scenario: Reject an invalid budget

- **WHEN** an administrator requests fewer than 1 or more than 100 capture slots
- **THEN** the system rejects the request without changing the current budget

### Requirement: Administrators can disable verbose capture

The system SHALL let an administrator disable verbose capture for an API key before its budget is exhausted. Disabling capture MUST set the remaining count to zero and MUST NOT delete captures already stored.

#### Scenario: Disable an active capture

- **WHEN** an administrator disables a key with 6 capture slots remaining
- **THEN** the key reports zero capture slots remaining
- **AND** later requests are not captured unless the key is armed again

### Requirement: Eligible request capture is atomic and self-disabling

An eligible request SHALL be a non-empty JSON HTTP request authenticated by the armed API key on a proxy route. Each eligible request MUST atomically claim at most one capture slot and persist at most one capture record. Concurrent requests MUST NOT produce more capture records than the armed budget. Requests that are not eligible, including dashboard requests, bodyless requests, multipart uploads, and WebSocket frames, MUST NOT consume capture slots. When the final slot is claimed, the remaining count SHALL become zero without a separate disable operation.

#### Scenario: Final slot disables capture

- **WHEN** an eligible request uses the only remaining capture slot
- **THEN** that request input is captured
- **AND** the key reports zero capture slots remaining
- **AND** the next eligible request is not captured

#### Scenario: Concurrent requests respect the budget

- **WHEN** more eligible requests arrive concurrently than the number of slots remaining
- **THEN** the number of new capture records does not exceed the remaining budget
- **AND** the remaining count does not become negative

#### Scenario: Ineligible request does not consume a slot

- **WHEN** an armed key authenticates a bodyless GET request or a multipart upload
- **THEN** no capture is stored
- **AND** the remaining count is unchanged

### Requirement: Captured inputs are bounded and exclude credentials

The system MUST store the request method, route path, content type, request identifier, capture time, and at most 262144 bytes of the request body. If a body exceeds that limit, the system SHALL store a UTF-8-safe prefix and mark the capture as truncated. The system MUST NOT persist authorization headers or other request headers in a verbose capture.

#### Scenario: Capture a normal JSON request

- **WHEN** an eligible JSON request body is no larger than 262144 bytes
- **THEN** the full body is stored with `truncated = false`
- **AND** no authorization header is stored

#### Scenario: Capture an oversized JSON request

- **WHEN** an eligible JSON request body exceeds 262144 bytes
- **THEN** only a UTF-8-safe prefix of at most 262144 bytes is stored
- **AND** the capture is marked `truncated = true`

### Requirement: Captured input is restricted to administrators

The request-log list SHALL indicate whether a request has captured input without embedding the input in the list response. The system SHALL provide captured input details only to authenticated dashboard administrators. Read-only guests MUST NOT receive captured payload content.

#### Scenario: Administrator views captured input

- **WHEN** an administrator opens details for a request with a capture
- **THEN** the dashboard shows the captured body and its truncation state

#### Scenario: Read-only guest requests captured input

- **WHEN** a read-only dashboard guest calls the captured-input detail endpoint
- **THEN** the system rejects the request without returning payload content

### Requirement: Capture lifecycle follows diagnostic data lifecycle

Deleting an API key MUST delete its stored verbose captures. Request-log retention MUST delete verbose captures older than the same effective request-log cutoff. Enabling or disabling capture MUST create an audit event that identifies the key and configured count but excludes captured input.

#### Scenario: Retention prunes captured input

- **WHEN** request-log retention runs with a cutoff that includes a verbose capture
- **THEN** the verbose capture is deleted in the same retention pass

#### Scenario: Audit an enable action

- **WHEN** an administrator arms a key for 10 requests
- **THEN** an audit event records the key identifier and count
- **AND** the audit event contains no request input
