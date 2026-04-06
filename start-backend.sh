#!/bin/bash
# Start backend server

cd "$(dirname "$0")"

# Optional: Set proxy if needed for network access
# export https_proxy=http://127.0.0.1:10887
# export http_proxy=http://127.0.0.1:10887

# Start backend using the virtual environment
./backend/.venv/bin/python -m uvicorn backend.main:app --port 8000 "$@"
