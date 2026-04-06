## ADDED Requirements

### Requirement: Agent initialization with MiniMax
The system SHALL initialize a LangChain agent with MiniMax LLM via OpenAI-compatible API.

#### Scenario: Successful initialization
- **WHEN** the test script runs with valid MINIMAX_API_KEY
- **THEN** the ChatOpenAI client connects to MiniMax endpoint without error

#### Scenario: Invalid API key
- **WHEN** the test script runs with invalid MINIMAX_API_KEY
- **THEN** the system returns an authentication error

### Requirement: Agent can answer a question
The system SHALL use DeepAgent with MiniMax to answer a user question.

#### Scenario: Agent responds to math question
- **WHEN** user asks "What is 2+2?"
- **THEN** agent returns a response containing "4"

#### Scenario: Agent responds to general knowledge question
- **WHEN** user asks "What is the capital of France?"
- **THEN** agent returns a response containing "Paris"
