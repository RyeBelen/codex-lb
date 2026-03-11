# Sticky Session Operations Specification

## Purpose

Define how sticky-session mappings are typed, managed, and cleaned up so bounded prompt-cache affinity remains operationally controllable without affecting durable routing modes.

## Requirements
### Requirement: Sticky sessions are explicitly typed
The system SHALL persist each sticky-session mapping with an explicit kind so durable Codex backend affinity, durable dashboard sticky-thread routing, and bounded prompt-cache affinity can be managed independently.

#### Scenario: Backend Codex session affinity is stored as durable
- **WHEN** a backend Codex request creates or refreshes stickiness from `session_id`
- **THEN** the stored mapping kind is `codex_session`

#### Scenario: Dashboard sticky thread routing is stored as durable
- **WHEN** sticky-thread routing creates or refreshes stickiness from a prompt-derived key
- **THEN** the stored mapping kind is `sticky_thread`

#### Scenario: OpenAI prompt-cache affinity is stored as bounded
- **WHEN** an OpenAI-style request creates or refreshes prompt-cache affinity
- **THEN** the stored mapping kind is `prompt_cache`

### Requirement: Dashboard exposes sticky-session administration
The system SHALL provide dashboard APIs for listing sticky-session mappings, deleting one mapping, and purging stale mappings.

#### Scenario: List sticky-session mappings
- **WHEN** the dashboard requests sticky-session entries
- **THEN** the response includes each mapping's `key`, `account_id`, `kind`, `created_at`, `updated_at`, `expires_at`, and `is_stale`

#### Scenario: Delete one mapping
- **WHEN** the dashboard deletes a sticky-session mapping by key
- **THEN** the system removes that mapping and returns a success response

#### Scenario: Purge stale prompt-cache mappings
- **WHEN** the dashboard requests a stale purge
- **THEN** the system deletes only stale `prompt_cache` mappings and leaves durable mappings untouched

### Requirement: Prompt-cache mappings are cleaned up proactively
The system SHALL run a background cleanup loop that deletes stale `prompt_cache` mappings using the current dashboard prompt-cache affinity TTL.

#### Scenario: Cleanup loop removes stale prompt-cache mappings
- **WHEN** the cleanup loop runs and finds `prompt_cache` mappings older than the configured TTL
- **THEN** it deletes those mappings

#### Scenario: Cleanup loop preserves durable mappings
- **WHEN** the cleanup loop runs
- **THEN** it does not delete `codex_session` or `sticky_thread` mappings regardless of age
