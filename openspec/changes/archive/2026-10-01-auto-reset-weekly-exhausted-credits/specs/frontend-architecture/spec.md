## ADDED Requirements

### Requirement: Per-account weekly-empty reset preference
The account detail action area SHALL expose an accessible default-off switch labeled “Auto-reset when weekly quota is empty” with help explaining weekly 0 percent, credit expiry within seven days and natural weekly refresh at least 24 hours away. It SHALL explain that the existing global five-minute fallback is independent. The UI SHALL save through the existing account PATCH/update mutation and invalidate account queries. It SHALL follow busy/write-access controls. Missing fields in older responses SHALL default false. No new global Settings control SHALL be added.

#### Scenario: Save one account's early reset choice
- **WHEN** the operator enables the weekly-empty switch for account A
- **THEN** the account PATCH sets `autoRedeemResetCreditsWhenWeeklyExhausted` true for A, leaves B unchanged, and preserves the global five-minute preference
