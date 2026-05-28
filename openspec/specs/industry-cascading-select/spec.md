# industry-cascading-select Specification

## Purpose
TBD - created by archiving change user-select-index. Update Purpose after archive.
## Requirements
### Requirement: Two-level cascading industry dropdown
The industry selection SHALL support two levels: Level-1 (一级行业) and Level-2 (二级行业/行业汇总).

#### Scenario: Level-1 dropdown shows all 申万一级行业
- **WHEN** user views the industry metrics panel
- **THEN** first dropdown displays all 28 申万一级行业 options
- **AND** first option is selected by default

#### Scenario: Level-2 dropdown appears after Level-1 selection
- **WHEN** user selects a Level-1 industry
- **THEN** second dropdown becomes enabled
- **AND** second dropdown shows "行业汇总" plus sub-industries for selected Level-1
- **AND** "行业汇总" is selected by default

#### Scenario: Select 行业汇总 shows Level-1 aggregated metrics
- **WHEN** user selects "行业汇总" from Level-2 dropdown
- **THEN** metrics and chart display for the Level-1 industry
- **AND** the displayed data is the aggregated industry-level metrics

#### Scenario: Select specific sub-industry shows sub-industry metrics
- **WHEN** user selects a specific sub-industry from Level-2 dropdown
- **THEN** metrics and chart display for that sub-industry
- **AND** the displayed data is the specific sub-industry metrics

### Requirement: Level-2 dropdown dynamically loads based on Level-1
The Level-2 options SHALL be fetched dynamically when Level-1 selection changes.

#### Scenario: Level-2 options update when Level-1 changes
- **WHEN** user selects a different Level-1 industry
- **THEN** Level-2 dropdown is reset to "行业汇总"
- **AND** Level-2 options refresh to show sub-industries for new Level-1

#### Scenario: Level-2 shows only 行业汇总 if no sub-industries exist
- **WHEN** Level-1 industry has no sub-industries in API response
- **THEN** Level-2 dropdown shows only "行业汇总" option
- **AND** Level-2 dropdown is disabled

### Requirement: API endpoint for sub-industry list
The system SHALL provide an endpoint to fetch sub-industries for a given Level-1 industry.

#### Scenario: Fetch sub-industries by parent ts_code
- **WHEN** frontend requests `/api/index/industry/subindustry?ts_code=xxx`
- **THEN** API returns list of sub-industries belonging to the specified parent industry
- **AND** each sub-industry has `ts_code` and `name` fields

### Requirement: Default to 行业汇总 on initial load
The Level-2 dropdown SHALL default to "行业汇总" when the panel loads.

#### Scenario: Initial load defaults Level-2 to 行业汇总
- **WHEN** IndexMetricsPanel loads and Level-1 industry is auto-selected
- **THEN** Level-2 defaults to "行业汇总"
- **AND** metrics displayed are for the Level-1 industry (aggregated)

