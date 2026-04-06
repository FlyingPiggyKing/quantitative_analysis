"""Test script to verify LangChain DeepAgent with MiniMax LLM."""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY")
if not MINIMAX_API_KEY:
    print("ERROR: MINIMAX_API_KEY not found in environment")
    exit(1)

print(f"MINIMAX_API_KEY found: {MINIMAX_API_KEY[:10]}...")

from deepagents import create_deep_agent
from langchain_openai import ChatOpenAI

print("\n1. Initializing ChatOpenAI with MiniMax...")

# MiniMax model
model = ChatOpenAI(
    model="MiniMax-M2.7",
    openai_api_key=MINIMAX_API_KEY,
    openai_api_base="https://api.minimax.chat/v1",
    temperature=0,
)

print("   ChatOpenAI initialized!")

print("\n2. Creating DeepAgent...")

# Create DeepAgent (no tools - just testing LLM call)
agent = create_deep_agent(
    model=model,
    system_prompt="You are a helpful assistant. Answer questions directly.",
)

print("   DeepAgent created!")

print("\n3. Testing agent with question.")
print("=" * 60)

try:
    # Invoke the agent
    result = agent.invoke({
        "messages": [{"role": "user", "content": "search the network, what is the break new for AI today?"}]
    })

    print("=" * 60)
    print("\n4. RESULT:")

    # Extract the final response
    messages = result.get("messages", [])
    if messages:
        final_msg = messages[-1]
        print(f"   Response: {final_msg.content}")

    print("\n✓ DeepAgent test passed! LangChain DeepAgent works with MiniMax!")
except Exception as e:
    print("=" * 60)
    print(f"\n4. ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    print("\n✗ Test failed. See error above for details.")
