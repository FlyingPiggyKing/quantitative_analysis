## ADDED Requirements

### Requirement: Output validation and retry on malformed JSON
The system SHALL validate LLM output from the stock trend analysis agent and retry if the output is malformed (contains reasoning markers or fails JSON parsing).

#### Scenario: Valid JSON output on first attempt
- **WHEN** LLM returns output that parses as valid JSON
- **AND** contains required fields: `trend_direction`, `confidence`
- **THEN** the system SHALL return the parsed result immediately
- **AND** no retry shall occur

#### Scenario: Malformed output with reasoning markers
- **WHEN** LLM returns output containing `<think>` or `</think>` markers
- **THEN** the system SHALL first strip those markers using regex
- **AND** then extract the JSON object using bracket-counting (handles nested structures)
- **AND** if parsing succeeds and required fields are valid, return the result
- **AND** if parsing fails, treat as malformed and proceed to retry

#### Scenario: Malformed output triggers retry
- **WHEN** output fails JSON parsing after marker stripping
- **THEN** the system SHALL retry the same LLM call up to 2 times
- **AND** each retry SHALL use the identical input (same prompt, same stock data)
- **AND** on each retry, validation SHALL be applied again

#### Scenario: All retries exhausted
- **WHEN** 3 total attempts (initial + 2 retries) all produce malformed output
- **THEN** the system SHALL return a fallback response with:
  - Same `symbol` and `name` from the input
  - `trend_direction`: "neutral"
  - `confidence`: 0
  - `summary`: "Analysis could not produce valid output after retries. Please try again later."
- **AND** the system SHALL log the failure with the raw output for debugging

### Requirement: Required fields validation
The system SHALL validate that the parsed output contains the required fields from the LLM before accepting it as valid. Note: `symbol` and `name` are added by the caller, not the LLM.

#### Scenario: Missing optional fields
- **WHEN** parsed JSON contains required fields (`trend_direction`, `confidence`)
- **AND** missing optional fields like `情绪分析`, `技术分析`, `趋势判断`, or `summary` at top level
- **THEN** the system SHALL accept the output as valid
- **AND** only the provided fields SHALL be included in the returned result
- **AND** `symbol` and `name` SHALL be added by the caller
- **AND** `summary` SHALL be derived from `趋势判断.forecast` if available

#### Scenario: Missing required fields
- **WHEN** parsed JSON is missing `trend_direction` or `confidence`
- **THEN** the system SHALL treat the output as malformed
- **AND** proceed to retry if retries remain

### Requirement: JSON extraction using bracket counting
The system SHALL extract JSON using bracket-counting to properly handle nested JSON structures, even when thinking markers are embedded within the JSON.

#### Scenario: Thinking markers inside JSON string values
- **WHEN** output contains `<think>...` blocks inside string values (e.g., inside news summaries)
- **THEN** the regex stripping SHALL remove those blocks first
- **AND** bracket-counting SHALL then correctly find the complete JSON object
- **AND** the JSON parsing SHALL succeed

#### Scenario: Content outside JSON preserved
- **WHEN** output is: `<think>...</think>{"foo": "bar"}<think>...`
- **THEN** regex stripping SHALL produce `{"foo": "bar"}`
- **AND** the JSON shall be valid

#### Scenario: Multiple markers stripped
- **WHEN** output contains multiple `<think>...` blocks
- **THEN** all blocks SHALL be removed before JSON extraction