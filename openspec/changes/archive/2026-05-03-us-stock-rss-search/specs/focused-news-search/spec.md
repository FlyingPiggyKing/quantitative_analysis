## ADDED Requirements

### Requirement: Focused MiniMax search for selected news
The system SHALL perform focused MiniMax searches using the selected Top 5 news titles to gather additional details.

#### Scenario: Search with selected news titles
- **WHEN** Agent provides Top 5 selected news items (title, description, link, pubDate)
- **THEN** for each item, perform a MiniMax search using the news title as query
- **AND** set max_results=3 and time_range="week"
- **AND** combine all search results for final analysis

#### Scenario: Merge RSS and search results
- **WHEN** MiniMax searches complete for all Top 5 items
- **THEN** merge the RSS news items with MiniMax search results
- **AND** format as combined news context for the analysis Agent
- **AND** present in a structure that includes: title, summary, source relevance

### Requirement: Fallback to existing search
If RSS fetch fails or returns empty results, the system SHALL fall back to the existing search_with_fallback approach.

#### Scenario: RSS fails, use existing search
- **WHEN** `fetch_yahoo_finance_rss()` returns empty list or error
- **THEN** use existing `search_with_fallback()` for news search
- **AND** proceed with existing workflow unchanged
