#!/bin/bash

# Start the overseas ETF fetcher-pusher daemon.
#
# Mirrors start.sh's style: kills any existing instance via PID file, then
# nohup-launches the daemon and writes the new PID. Logs go to logs/.

set -euo pipefail

# Get script directory (so this works from any CWD)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Create logs directory
mkdir -p "$SCRIPT_DIR/logs"

# Stop any previously-launched fetcher (avoid double-start)
PIDFILE="$SCRIPT_DIR/logs/remote_data.pid"
if [ -f "$PIDFILE" ]; then
  OLD_PID=$(cat "$PIDFILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stopping existing fetcher (PID $OLD_PID)..."
    kill "$OLD_PID" 2>/dev/null || true
    # Give it a moment to exit cleanly
    sleep 1
  fi
  rm -f "$PIDFILE"
fi

# Ensure remote_data schema exists (idempotent — the daemon also runs
# local_db.init() on startup, but doing it here gives a clean error if
# disk is full / read-only before the daemon tries).
echo "[start-fetcher] initializing local DB"
PYTHONPATH="$SCRIPT_DIR" ./remote_data/.venv/bin/python \
  remote_data/scripts/init_local_db.py

# Launch daemon in the background
cd "$SCRIPT_DIR"
nohup ./remote_data/.venv/bin/python -m remote_data \
  > "$SCRIPT_DIR/logs/remote_data.log" 2>&1 &
FETCHER_PID=$!
echo "$FETCHER_PID" > "$PIDFILE"
echo "Fetcher started with PID: $FETCHER_PID"

echo ""
echo "Service started:"
echo "  Fetcher:  http://127.0.0.1:8001/health (overseas box, localhost-only)"
echo ""
echo "Logs:"
echo "  Wrapper stdout: $SCRIPT_DIR/logs/remote_data.log"
echo "  Application:    $SCRIPT_DIR/logs/../remote_data/data/etf_local.log"
echo ""
echo "To stop: kill \"\$(cat $PIDFILE)\""