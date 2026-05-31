## MODIFIED Requirements

### Requirement: Search and trend analysis button layout
The homepage SHALL display the 查询 button in the search form. The homepage SHALL NOT display a batch 趋 势 分 析 button, because trend prediction is now system-managed (scheduled automatically and triggered only by admins from the System Administration module).

#### Scenario: Logged-out user sees single button
- **WHEN** an unauthenticated user views the homepage search form
- **THEN** only the "查 询" button is displayed
- **AND** it spans the full width of the form

#### Scenario: Logged-in user sees only the search button
- **WHEN** an authenticated user views the homepage search form
- **THEN** only the "查 询" button is displayed
- **AND** it spans the full width of the form
- **AND** no batch "趋 势 分 析" button is displayed
