#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 通过端口停止后端 (8000)
BACKEND_PID=$(lsof -ti:8000 2>/dev/null)
if [ -n "$BACKEND_PID" ]; then
    kill $BACKEND_PID 2>/dev/null
    echo "Backend stopped (PID: $BACKEND_PID, port 8000)"
else
    echo "Backend not running on port 8000"
fi

# 通过端口停止前端 (3000)
FRONTEND_PID=$(lsof -ti:3000 2>/dev/null)
if [ -n "$FRONTEND_PID" ]; then
    kill $FRONTEND_PID 2>/dev/null
    echo "Frontend stopped (PID: $FRONTEND_PID, port 3000)"
else
    echo "Frontend not running on port 3000"
fi

# 清理 PID 文件
rm -f "$SCRIPT_DIR/logs/backend.pid" "$SCRIPT_DIR/logs/frontend.pid" 2>/dev/null

echo "All services stopped."
