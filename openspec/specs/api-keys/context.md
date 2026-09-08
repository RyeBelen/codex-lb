# API key operational context

## GPT-6 Astra permission

Use **APIs > Edit API key > Allow GPT-6 Astra** to enable access for selected keys. New and existing keys default to off after migration. For example, enable the personal key and leave a shared key disabled to reserve Astra access for the personal key.

The permission is independent of Allowed models and Apply to codex /model. An enabled key still needs Astra in its allowlist when one is configured, an eligible account or model source, and quota. Enforcing Astra as the model does not grant permission. Calls without an authenticated key are denied Astra, even with proxy authentication disabled.

Permission updates use the existing authorization-cache invalidation interval across workers; in-flight requests are not canceled. The migration adds a false default for historical rows, so enable intended keys after upgrading. Reverting this feature restores the previous unrestricted policy.
