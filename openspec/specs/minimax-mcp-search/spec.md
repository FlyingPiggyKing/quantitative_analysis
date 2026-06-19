## ADDED Requirements

### Requirement: MiniMax MCP Web Search Tool
The system SHALL provide a web search tool backed by MiniMax MCP server that can be used as fallback when Tavily is unavailable.

#### Scenario: Search with MiniMax MCP
- **WHEN** `minimax_mcp_search` tool is invoked with a query string
- **THEN** the tool SHALL spawn the MiniMax MCP server via `uvx minimax-coding-plan-mcp -y`
- **AND** the tool SHALL send a JSON-RPC request via stdio to invoke the web search tool
- **AND** the tool SHALL return formatted search results matching Tavily's output format

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

### Requirement: Robust uvx Binary Resolution
The system SHALL locate the `uvx` binary reliably regardless of the calling process's `PATH`, because the MCP server is spawned as a subprocess and inherits the parent's environment.

#### Scenario: uvx is on PATH
- **WHEN** `shutil.which("uvx")` finds a binary on `PATH`
- **THEN** the MCP client SHALL use that absolute path as the `command`

#### Scenario: uvx is NOT on PATH but uv is
- **WHEN** `shutil.which("uvx")` returns None
- **AND** `shutil.which("uv")` returns a path
- **THEN** the resolver SHALL return the sibling `uvx` next to that `uv` binary
- **AND** the MCP client SHALL use that absolute path

#### Scenario: Neither uvx nor uv is on PATH
- **WHEN** neither `uvx` nor `uv` is found
- **THEN** the resolver SHALL return the bare string `"uvx"` and the spawn SHALL fail loudly with a clear `FileNotFoundError`

### Requirement: MCP Server Pre-installed by Start Script
The system SHALL ensure the `minimax-coding-plan-mcp` server is installed before the backend starts, so the first call does not block on PyPI resolution and works offline / offline-restricted environments.

#### Scenario: Local dev startup installs MCP server
- **WHEN** `./start-backend.sh` (or `./start.sh`) is invoked
- **THEN** it SHALL run `uv tool install minimax-coding-plan-mcp` (idempotent, no-op if already installed)
- **AND** it SHALL export `~/.local/bin` to `PATH` so the spawned MCP subprocess can find `uvx`
