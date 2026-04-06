## Why

We need to verify whether LangChain DeepAgent can work with MiniMax LLM via its OpenAI-compatible API. This is a spike/investigation to determine feasibility before committing to a full implementation.

## What Changes

1. Add MiniMax API key configuration to backend `.env`
2. Create a test script that:
   - Configures LangChain with MiniMax using OpenAI-compatible endpoint
   - Initializes a DeepAgent with MiniMax
   - Asks a simple question and verifies the agent returns a coherent response
3. Document whether the integration works and any issues encountered

## Capabilities

### New Capabilities
- `langchain-deepagent-minimax-test`: A test capability to verify LangChain DeepAgent works with MiniMax LLM provider via OpenAI-compatible API

### Modified Capabilities
- (none - this is a spike/test)

## Impact

- **Backend**: New test script `backend/test_minimax_agent.py`
- **Dependencies**: New packages `langchain`, `langchain-openai`, `langchain-core`
- **Configuration**: `MINIMAX_API_KEY` added to backend `.env`
