## ADDED Requirements

### Requirement: Add stock to watch list
The system SHALL allow adding a stock to the user's watch list by symbol and name.

#### Scenario: Successfully add a stock
- **WHEN** user clicks "Add to Watch List" on stock detail page
- **THEN** system stores the stock symbol and name in the database with current timestamp
- **AND** button changes to "Remove from Watch List"

#### Scenario: Add duplicate stock
- **WHEN** user attempts to add a stock that already exists in watch list
- **THEN** system returns HTTP 409 Conflict
- **AND** watch list is unchanged

### Requirement: Remove stock from watch list
The system SHALL allow removing a stock from the watch list.

#### Scenario: Successfully remove a stock
- **WHEN** user clicks "Remove from Watch List" on stock detail page
- **THEN** system deletes the stock from the database
- **AND** button changes to "Add to Watch List"

#### Scenario: Remove non-existent stock
- **WHEN** user attempts to remove a stock not in watch list
- **THEN** system returns HTTP 404 Not Found

### Requirement: List watch list with pagination
The system SHALL return watch list items with pagination support.

#### Scenario: Fetch first page of watch list
- **WHEN** user visits index page
- **THEN** system fetches watch list with page=1, page_size=10 by default
- **AND** returns total count and total_pages for pagination UI

#### Scenario: Fetch specific page and page size
- **WHEN** user selects page size of 20 and page 2
- **THEN** system returns items 21-40 of watch list
- **AND** page_size must be one of: 10, 20, 30

### Requirement: Check if stock is in watch list
The system SHALL provide an endpoint to check if a specific stock is in the watch list.

#### Scenario: Stock exists in watch list
- **WHEN** GET /api/watchlist/{symbol} is called for a watched stock
- **THEN** system returns HTTP 200 with stock details

#### Scenario: Stock not in watch list
- **WHEN** GET /api/watchlist/{symbol} is called for a non-watched stock
- **THEN** system returns HTTP 404 Not Found
