## ADDED Requirements

### Requirement: Mobile Header Adaptation
The page header SHALL be adapted for mobile with compact layout.

#### Scenario: Header on mobile index page
- **WHEN** index page renders on mobile
- **THEN** header SHALL display site title only (no full navigation bar)
- **AND** header height SHALL be compact (`h-12` to `h-14`)

#### Scenario: Search input on mobile
- **WHEN** stock search input renders on mobile
- **THEN** search input SHALL be full width
- **AND** search button SHALL be integrated or adjacent to input

### Requirement: Page Navigation on Mobile
Navigation between pages SHALL work with touch interactions.

#### Scenario: Navigate to stock detail from index
- **WHEN** user taps a stock card/row on index page mobile
- **THEN** app SHALL navigate to stock detail page for that symbol
- **AND** back button in browser SHALL return to index

#### Scenario: Back navigation on stock detail
- **WHEN** user is on stock detail page on mobile
- **THEN** browser back button SHALL return to index page
- **AND** header SHALL NOT duplicate back button (rely on browser chrome)

### Requirement: Pull-to-Refresh Pattern
Mobile pages SHALL support pull-to-refresh for data updates.

#### Scenario: Pull-to-refresh on index page
- **WHEN** user pulls down from top of index page on mobile
- **THEN** page SHALL refresh watchlist data
- **AND** show refresh indicator during load

#### Scenario: Pull-to-refresh on stock detail
- **WHEN** user pulls down from top of stock detail page on mobile
- **THEN** page SHALL refresh stock data and indicators
- **AND** show refresh indicator during load

### Requirement: Loading States on Mobile
Loading states SHALL be visible and appropriately sized for mobile.

#### Scenario: Initial page load skeleton
- **WHEN** page is loading on mobile
- **THEN** skeleton loaders SHALL display instead of content
- **AND** skeleton elements SHALL match mobile layout (not desktop)

#### Scenario: Button loading state
- **WHEN** action button (e.g., "Run Analysis") is clicked on mobile
- **THEN** button SHALL show loading spinner
- **AND** button SHALL be disabled during loading
