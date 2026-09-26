# Unavailable account catalogs

An account at its usage limit can be absent from the current resolved catalog even though its saved model reservations remain in the database. The reservation controls future routing and is separate from the current quota state, so the dashboard should still let an operator edit it.

For example, if a limited account is currently reserved for `gpt-6-astra`, the operator can remove Astra and select known `gpt-6-sol` before the limit resets. The UI marks Sol's support for that account as unverified until its catalog returns. Routing still checks the account's actual model capability and quota before sending a request.

Only saved selections and public subscription models known to the registry are accepted while account-specific evidence is missing. If the registry has no known choices, the operator can still remove saved selections. An empty selection remains unrestricted for whatever models the account supports after recovery.
