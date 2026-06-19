#!/bin/bash
# Start backend server

cd "$(dirname "$0")"

# Optional: Set proxy if needed for network access
# export https_proxy=http://127.0.0.1:10887
# export http_proxy=http://127.0.0.1:10887

# Set PYTHONPATH so 'backend' module can be imported
export PYTHONPATH="$(pwd)"

# Ensure uv-managed MCP server is installed (no-op once present)
export PATH="$HOME/.local/bin:$PATH"
uv tool install minimax-coding-plan-mcp >/dev/null 2>&1 || true

# Start backend using the virtual environment
./backend/.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 "$@"
