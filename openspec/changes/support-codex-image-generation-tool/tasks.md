## 1. Validation plumbing

- [x] 1.1 Add route-scoped built-in tool validation support to shared Responses normalization helpers.
- [x] 1.2 Validate backend HTTP and internal bridge Responses payloads with the backend Codex `image_generation` allowance while keeping `/v1` parsing unchanged.

## 2. Transport handling

- [x] 2.1 Pass the backend Codex `image_generation` allowance through websocket `response.create` preparation for `/backend-api/codex/responses`.
- [x] 2.2 Keep `/v1/responses` websocket validation strict and preserve backend upstream forwarding unchanged.

## 3. Verification

- [x] 3.1 Add regression tests for backend HTTP and websocket `image_generation` acceptance plus continued `/v1` rejection.
- [x] 3.2 Run targeted pytest coverage for backend responses and websocket tool validation paths.
