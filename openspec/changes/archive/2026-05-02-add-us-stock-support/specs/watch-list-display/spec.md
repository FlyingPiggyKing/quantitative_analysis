# watch-list-display Specification

## Purpose
Display user's watchlist with stock information, PE trends, and AI predictions in tabular format.

## ADDED Requirements

### Requirement: Market type in watchlist storage
The system SHALL store market type ("A" for A-share, "US" for US stocks) with each watchlist entry.

#### Scenario: Add A-share stock to watchlist
- **WHEN** user adds A-share stock (e.g., "600938") to watchlist
- **THEN** watchlist entry is created with symbol="600938", name="中海油服", market="A"

#### Scenario: Add US stock to watchlist
- **WHEN** user adds US stock (e.g., "GOOGL") to watchlist
- **THEN** watchlist entry is created with symbol="GOOGL", name="Google", market="US"

#### Scenario: Legacy watchlist entries have null market
- **WHEN** querying watchlist entries created before this change
- **THEN** market field is null, treated as "A" for backward compatibility

### Requirement: Watchlist display filters by market tab
The system SHALL filter watchlist display based on selected market tab.

#### Scenario: Display A-share stocks when A股 tab selected
- **WHEN** "A股" tab is selected
- **THEN** show only stocks where market="A" OR market IS NULL

#### Scenario: Display US stocks when 美股 tab selected
- **WHEN** "美股" tab is selected
- **THEN** show only stocks where market="US"
