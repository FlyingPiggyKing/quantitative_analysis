## MODIFIED Requirements

### Requirement: MiniMax MCP Web Search Tool
The system SHALL provide a web search tool backed by MiniMax MCP server that can be used as primary search when Tavily is unavailable.

#### Scenario: Search with MiniMax MCP
- **WHEN** `minimax_mcp_search` tool is invoked with a query string
- **THEN** the tool SHALL spawn the MiniMax MCP server via `uvx minimax-coding-plan-mcp -y`
- **AND** the tool SHALL send a JSON-RPC request via stdio to invoke the web search tool
- **AND** the tool SHALL return formatted search results matching Tavily's output format

#### Scenario: Time range filtering
- **WHEN** `minimax_mcp_search` is called with `time_range="month"`
- **THEN** the tool SHALL filter results to only include articles published within the last 30 days
- **AND** results outside this range SHALL be excluded from the returned list

#### Scenario: Handle MCP server failure
- **WHEN** the MiniMax MCP server fails to start or respond
- **THEN** the tool SHALL return an error message starting with "Search error:"
- **AND** the error SHALL not raise an exception (graceful degradation)

#### Scenario: Respect max_results parameter
- **WHEN** `minimax_mcp_search` is called with `max_results=N`
- **THEN** the tool SHALL request at most N results from the MCP server
- **AND** return at most N formatted results

#### Scenario: Handle empty results
- **WHEN** the MiniMax MCP server returns no results
- **THEN** the tool SHALL return "No search results found."

#### Scenario: Timeout protection
- **WHEN** the MCP server does not respond within timeout (30 seconds)
- **THEN** the tool SHALL return "Search error: Timeout communicating with MCP server"
