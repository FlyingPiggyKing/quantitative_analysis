## ADDED Requirements

### Requirement: Search Fallback Chain
The system SHALL provide a search fallback chain that prioritizes MiniMax MCP over Tavily for stock news search.

#### Scenario: Primary search via MiniMax MCP
- **WHEN** agent performs stock news search
- **THEN** system SHALL first attempt MiniMax MCP search
- **AND** if MiniMax MCP returns results, use those results

#### Scenario: Fallback to Tavily
- **WHEN** MiniMax MCP returns no results or an error
- **THEN** system SHALL fallback to Tavily search
- **AND** continue analysis using Tavily results

#### Scenario: Both sources fail
- **WHEN** both MiniMax MCP and Tavily return errors or no results
- **THEN** agent SHALL return "neutral" trend with 0% confidence
- **AND** summary SHALL state "Insufficient recent news data for analysis"
