## ADDED Requirements

### Requirement: Money Flow Data Injection into AI Agent
The system SHALL inject the latest 5-day money flow data into the AI trend prediction agent as part of the technical data context.

#### Scenario: Money flow data fetched successfully
- **WHEN** `analyze_stock_trend()` is called for a stock
- **THEN** system SHALL fetch money flow data via `stock_service.get_moneyflow(symbol, days=5)`
- **AND** if fetch succeeds, money flow data SHALL be passed to `format_data_context()`
- **AND** money flow context SHALL be included in the user message sent to the AI agent

#### Scenario: Money flow data fetch fails
- **WHEN** `get_moneyflow()` returns an error or raises an exception
- **THEN** system SHALL proceed without money flow data
- **AND** the AI agent SHALL perform analysis using available technical data only
- **AND** no error SHALL be surfaced to the caller

### Requirement: Money Flow Context Formatting
The system SHALL append money flow data to the existing valuation/估值 section in `format_data_context()`.

#### Scenario: Format money flow merged with valuation section
- **WHEN** money flow data is available for a stock
- **THEN** the 5-day cumulative net inflow/outflow SHALL be appended to the valuation section
- **AND** the line SHALL show: net amount in 万元 and a signal (净流入偏多/净流出偏多/持平)
- **AND** it SHALL appear after PE, PB, 换手率, 总市值 lines

#### Scenario: Money flow data unavailable
- **WHEN** money flow fetch fails or returns an error
- **THEN** the valuation section SHALL be formatted without money flow
- **AND** no money flow line SHALL appear

### Requirement: Money Flow in System Prompt
The system prompt SHALL instruct the AI agent to analyze money flow signals as part of technical analysis.

#### Scenario: System prompt includes money flow instruction
- **WHEN** `get_system_prompt()` is called
- **THEN** the prompt SHALL list money flow signals (主力净流入/净流出) as one of the technical data points to analyze
- **AND** the prompt SHALL reference the money flow context section in the user message

### Requirement: Money Flow in Technical Analysis Output
The AI agent SHALL include money flow signals in the `技术分析` section of its structured output.

#### Scenario: Agent returns money flow in technical analysis
- **WHEN** the AI agent produces a valid prediction response
- **THEN** the `技术分析` object SHALL contain a `money_flow` sub-object
- **AND** `money_flow` SHALL include: `net_5d` (5-day cumulative), `signal` (净流入偏多/净流出偏多/持平), and `interpretation` (brief analysis)

#### Scenario: Agent output parsing handles missing money_flow
- **WHEN** the AI agent response lacks `money_flow` in `技术分析`
- **THEN** the parsing SHALL NOT fail
- **AND** `技术分析.money_flow` SHALL be set to `null` or omitted
