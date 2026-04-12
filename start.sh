#!/bin/bash

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 创建日志目录
mkdir -p "$SCRIPT_DIR/logs"

# 启动后端 (FastAPI/uvicorn)
cd "$SCRIPT_DIR"
nohup ./backend/.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 > "$SCRIPT_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# 构建前端 (Next.js production build)
cd "$SCRIPT_DIR/frontend"
npm run build > "$SCRIPT_DIR/logs/frontend_build.log" 2>&1
echo "Frontend build completed"

# 启动前端 (Next.js production)
cd "$SCRIPT_DIR/frontend"
nohup npm start > "$SCRIPT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

# 保存 PIDs
echo "$BACKEND_PID" > "$SCRIPT_DIR/logs/backend.pid"
echo "$FRONTEND_PID" > "$SCRIPT_DIR/logs/frontend.pid"

echo ""
echo "Services started:"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo ""
echo "Logs:"
echo "  Backend:  $SCRIPT_DIR/logs/backend.log"
echo "  Frontend: $SCRIPT_DIR/logs/frontend.log"
