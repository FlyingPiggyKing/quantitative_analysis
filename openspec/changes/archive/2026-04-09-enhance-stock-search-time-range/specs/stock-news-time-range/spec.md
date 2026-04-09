## ADDED Requirements

### Requirement: Stock news time range filter
The Tavily search tool SHALL filter news results to only return articles from the current week when searching for stock-related news.

#### Scenario: Search with week time range
- **WHEN** agent calls tavily_search with topic="finance" for stock news
- **THEN** system SHALL set time_range="week" to filter results to current 7 days

#### Scenario: Limit to 5 latest news results
- **WHEN** agent calls tavily_search for stock-specific news
- **THEN** system SHALL return exactly 5 results (max_results=5)
- **AND** results SHALL be ordered by relevance within the time range
