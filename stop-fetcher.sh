#!/bin/bash

# Stop the overseas ETF fetcher-pusher daemon.
#
# Mirrors start-fetcher.sh: reads the PID from logs/remote_data.pid, sends
# SIGTERM, waits for graceful exit, then removes the PID file. Falls back to
# SIGKILL if the daemon doesn't exit within 10 seconds.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="$SCRIPT_DIR/logs/remote_data.pid"

if [ ! -f "$PIDFILE" ]; then
  echo "No PID file at $PIDFILE — daemon is not running (or wasn't started via start-fetcher.sh)."
  exit 0
fi

PID=$(cat "$PIDFILE")

if ! kill -0 "$PID" 2>/dev/null; then
  echo "PID $PID is not alive. Cleaning up stale PID file."
  rm -f "$PIDFILE"
  exit 0
fi

echo "Stopping fetcher (PID $PID)..."
kill "$PID"

# Wait up to 10 seconds for graceful exit
for i in 1 2 3 4 5 6 7 8 9 10; do
  if ! kill -0 "$PID" 2>/dev/null; then
    rm -f "$PIDFILE"
    echo "Fetcher stopped."
    exit 0
  fi
  sleep 1
done

# Still alive — force-kill
echo "Fetcher did not exit within 10s. Sending SIGKILL..."
kill -9 "$PID" 2>/dev/null || true
rm -f "$PIDFILE"
echo "Fetcher force-stopped."