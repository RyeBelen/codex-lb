## ADDED Requirements

### Requirement: Production and verbose-capture migration lineages converge safely

The migration graph SHALL recognize databases stamped at `20260726_000000_repair_request_usage_rollups_after_merge` and SHALL converge that production lineage with `20260824_000000_add_api_key_verbose_capture` at one forward-only Alembic head. The upgrade MUST NOT require a database downgrade, manual stamp, or rewrite of an already merged revision. ORM metadata and required manual indexes MUST match the resulting schema so post-upgrade drift checks pass.

#### Scenario: Existing production database upgrades to the merged head

- **GIVEN** a database is stamped at `20260726_000000_repair_request_usage_rollups_after_merge`
- **WHEN** startup upgrades the database to Alembic head
- **THEN** the verbose-capture schema is applied
- **AND** the database reaches the single merged head
- **AND** schema drift checking reports no differences

#### Scenario: Fresh database follows the combined graph

- **GIVEN** an empty supported database
- **WHEN** migrations upgrade it to Alembic head
- **THEN** the production-line and verbose-capture schemas are both present
- **AND** exactly one Alembic head remains
