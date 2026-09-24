## MODIFIED Requirements

### Requirement: Dashboard rule management
Authenticated dashboard users SHALL view an account's current allowed-model selections and resolved supported subscription models from that account's detail view. Dashboard writers SHALL atomically replace all allowed-model selections for one account. No selection SHALL mean the account is unrestricted and can serve every model it otherwise supports; one or more selections SHALL restrict the account to those exact model IDs. The editor SHALL render the resolved models as checkboxes, explain empty-selection behavior, support explicit save/reload, and honor read-only access. A selected model that is no longer in the resolved catalog SHALL remain visible as unavailable and removable. When the account catalog is unavailable, the dashboard SHALL distinguish that state from an empty resolved catalog and SHALL NOT offer a write based on missing catalog evidence. The previous global Settings editor SHALL NOT be presented, while the existing model-oriented backend API SHALL remain compatible.

#### Scenario: Show the resolved account catalog
- **WHEN** an authenticated user opens an account whose model catalog is resolved
- **THEN** the account detail shows a checkbox for each supported subscription model and checks the account's current selections

#### Scenario: Restrict one account to selected models
- **WHEN** a dashboard writer selects Astra and Sol for an account and saves
- **THEN** the account is atomically restricted to Astra and Sol while other accounts' selections remain unchanged

#### Scenario: Clear all selections
- **WHEN** a dashboard writer clears every model checkbox and saves
- **THEN** all model grants for that account are removed and the account returns to ordinary eligibility for every model it supports

#### Scenario: Keep stale selections visible
- **WHEN** a selected model is absent from the account's current resolved catalog
- **THEN** the editor shows the model as an unavailable checked selection that the writer can remove

#### Scenario: Account catalog unavailable
- **WHEN** no resolved or retained model catalog exists for the account
- **THEN** the editor reports that the catalog is unavailable and does not allow a replacement write

#### Scenario: Reject invalid account update
- **WHEN** a writer submits a newly selected model outside the account's resolved catalog, names an unknown or pending-deletion account, or a read-only viewer submits an update
- **THEN** the update fails without changing any stored grants
