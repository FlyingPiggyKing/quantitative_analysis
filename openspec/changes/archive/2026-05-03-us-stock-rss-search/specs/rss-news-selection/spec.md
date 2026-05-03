## ADDED Requirements

### Requirement: Agent selects Top 5 news from RSS list
The stock trend analysis Agent SHALL select the top 5 most important and timely news items from the RSS news list based on relevance to the target stock.

#### Scenario: Agent selects Top 5 from RSS items
- **WHEN** Agent receives a list of RSS news items (title, description, link, pubDate)
- **THEN** the Agent SHALL evaluate each item for:
  - Relevance to the target stock symbol/name
  - Recency (newer items preferred)
  - Potential market impact (earnings, M&A, regulatory news prioritized)
- **AND** select exactly 5 items (or fewer if list has fewer than 5 items)

#### Scenario: Selection criteria
- **WHEN** Agent evaluates RSS news items
- **THEN** priority SHALL be given to:
  - Items mentioning the stock symbol directly
  - Items with recent publication dates
  - Items about significant events (earnings, mergers, regulatory decisions)
- **AND** items about unrelated markets or outdated information SHALL be deprioritized

#### Scenario: Return selected news with search queries
- **WHEN** Agent completes selection
- **THEN** return a list of selected items
- **AND** for each item, generate a search query string combining title + stock name for MiniMax search
