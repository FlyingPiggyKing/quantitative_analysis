## MODIFIED Requirements

### Requirement: Section header for PresetStockList
The system SHALL display a section header "热门股" above the market tab bar in PresetStockList for guest users.

#### Scenario: Guest views PresetStockList with section header
- **WHEN** guest user visits homepage
- **THEN** PresetStockList displays header "热门股" with decorative brass styling
- **AND** market tabs (A股, 港股, 美股) appear below the header

#### Scenario: Guest views PresetStockList on mobile
- **WHEN** guest user visits homepage on mobile device
- **THEN** PresetStockList displays "热门股" header
- **AND** market tabs appear below in scrollable tab bar
