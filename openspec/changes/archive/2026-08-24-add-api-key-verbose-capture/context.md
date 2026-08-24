## Purpose and scope

Verbose capture is a short diagnostic mode for answering questions such as, "What inputs are driving this key's unexpected token usage?" It is intentionally per key and finite. It is not a general traffic archive.

## Rationale

Global payload logging affects every caller and can persist sensitive data indefinitely. A bounded database-backed budget makes the operator's intent visible, works across replicas, and automatically returns the system to metadata-only logging.

## Constraints and failure modes

- Only administrators can arm, disable, or read captured inputs.
- Capture must not include authorization or arbitrary headers.
- JSON bodies may be large, so each stored input is capped at 256 KiB and marked when truncated.
- Concurrent requests must share one database counter; process-local state is insufficient.
- A crash after capture but before normal request-log persistence can leave an orphan capture; retention removes it using its capture timestamp.

## Example flow

1. An administrator selects an API key and arms verbose capture for 10 requests.
2. The next 10 eligible JSON proxy calls decrement the count from 10 to 0 and persist their bounded inputs.
3. The key automatically returns to metadata-only logging at zero.
4. Request Logs marks those rows as having captured input. Opening a marked row fetches the input through the administrator-only details endpoint.
5. The administrator can re-arm the key with a different count or disable it early without deleting already captured diagnostics.

## Operational notes

Audit records identify who changed capture state, the key, and the requested count; they never contain captured bodies. Normal request-log retention governs capture cleanup so operators do not need a second retention setting.

## Intentional limitations

- Capture is limited to non-empty JSON HTTP request bodies; it does not archive responses, headers, multipart uploads, WebSocket frames, or complete conversations.
- An orphan capture whose normal request log never persists remains subject to retention but is not discoverable through the request-log details UI.
- The repository has no API-key or request-log screenshot baseline; verification uses component interaction tests, mock-handler coverage, and a production frontend build instead.
