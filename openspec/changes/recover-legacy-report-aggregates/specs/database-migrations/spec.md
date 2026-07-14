## ADDED Requirements

### Requirement: Legacy aggregate archive migration is forward-only and portable

The database migration MUST add the immutable legacy aggregate archive with the
same logical constraints on SQLite and PostgreSQL, MUST preserve a single
Alembic head, and MUST NOT recreate the retired aggregate-fold scheduler.

#### Scenario: Empty database upgrades to the archive schema

- **WHEN** an empty SQLite or PostgreSQL database upgrades to head
- **THEN** the legacy aggregate archive and evidence-based indexes exist
- **AND** the migration graph has one head

