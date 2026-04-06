## ADDED Requirements

### Requirement: Display watch list on index page
The system SHALL display the user's watch list below the stock search input on the index page.

#### Scenario: Watch list has items
- **WHEN** user has stocks in watch list
- **THEN** system displays a table/grid showing: symbol, name, added date
- **AND** each row links to the stock detail page

#### Scenario: Watch list is empty
- **WHEN** user has no stocks in watch list
- **THEN** system displays message: "Your watch list is empty. Search for a stock to get started."

### Requirement: Pagination controls
The system SHALL allow user to select number of rows per page (10, 20, 30).

#### Scenario: Change page size
- **WHEN** user clicks page size selector
- **THEN** system re-fetches watch list with new page_size
- **AND** selected page resets to 1

### Requirement: Add to watch list button on detail page
The system SHALL display "Add to Watch List" or "Remove from Watch List" button on stock detail page.

#### Scenario: Stock not in watch list
- **WHEN** user views stock detail page for non-watched stock
- **THEN** system displays "Add to Watch List" button

#### Scenario: Stock already in watch list
- **WHEN** user views stock detail page for watched stock
- **THEN** system displays "Remove from Watch List" button

#### Scenario: Click add button
- **WHEN** user clicks "Add to Watch List" button
- **THEN** button changes to "Remove from Watch List"
- **AND** watch list count updates on index page

#### Scenario: Click remove button
- **WHEN** user clicks "Remove from Watch List" button
- **THEN** button changes to "Add to Watch List"
- **AND** stock disappears from watch list on next index page visit
