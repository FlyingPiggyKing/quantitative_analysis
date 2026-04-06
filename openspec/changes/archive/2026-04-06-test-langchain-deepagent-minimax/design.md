## Context

This is a **spike/test** to verify LangChain DeepAgent compatibility with MiniMax LLM.

**MiniMax API Details:**
- Endpoint: `https://api.minimax.chat/v1` (OpenAI-compatible)
- Model: `MiniMax-Text-01` or similar
- API Key provided by user

**LangChain DeepAgent:**
- Experimental agent in LangChain
- Works with any LLM implementing the chat model interface
- If MiniMax has OpenAI-compatible API, it should work via `langchain-openai` with custom `base_url`

## Goals / Non-Goals

**Goals:**
- Create a minimal test script that initializes DeepAgent with MiniMax
- Verify agent can process a user question and return a response
- Document pass/fail and any error messages

**Non-Goals:**
- Full agent integration with stock analysis features
- Production-ready code
- Error handling for all edge cases

## Decisions

### 1. Use `langchain-openai` with custom base_url

**Decision:** Configure `ChatOpenAI` from `langchain-openai` with MiniMax's OpenAI-compatible endpoint.

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="MiniMax-Text-01",  # or appropriate MiniMax model name
    openai_api_key=os.environ["MINIMAX_API_KEY"],
    openai_api_base="https://api.minimax.chat/v1"
)
```

**Rationale:** MiniMax provides OpenAI-compatible API. This avoids needing a custom MiniMax integration.

### 2. Use LangChain's built-in DeepAgent

**Decision:** Use `from langchain.agents import Agent` with `DeepAgent` or similar.

**Rationale:** We're testing whether the *combination* works, not building custom agent logic.

## Test Script Design

```
test_minimax_agent.py
├── Load MINIMAX_API_KEY from env
├── Initialize ChatOpenAI with MiniMax endpoint
├── Create a simple agent (e.g., zero-shot-react)
├── Ask test question: "What is 2+2?"
└── Print response or error
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| MiniMax API key is invalid | Script will fail with auth error - user must verify |
| MiniMax model name is wrong | May need to try different model names from their docs |
| LangChain version incompatibility | Pin to stable langchain version |

## Open Questions

1. **What is the exact model name for MiniMax?** Need to verify from MiniMax API docs
2. **Does MiniMax support function calling?** Required for some agent types
