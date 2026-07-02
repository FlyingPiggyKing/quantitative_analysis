#!/bin/bash

# Verify the overseas ETF fetcher-pusher side is healthy.
#
# Run from the overseas box. Exits 0 on success, non-zero on any check failure.
#
# Uses Python's stdlib `sqlite3` — no external CLI needed.

set -e

# Locate repo
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REMOTE_DIR="$SCRIPT_DIR/remote_data"

# Configurable via env (defaults match the standard deploy)
DB_PATH="${DB_PATH:-$REMOTE_DIR/data/etf_local.db}"
LOG_FILE="${LOG_FILE:-$SCRIPT_DIR/logs/remote_data.log}"
PIDFILE="${PIDFILE:-$SCRIPT_DIR/logs/remote_data.pid}"
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:8001/health}"
DOMESTIC_BASE="${DOMESTIC_BASE:-https://www.51stock.com.cn}"
DOMESTIC_HEALTH="${DOMESTIC_BASE}/health"
PYTHON_BIN="${PYTHON_BIN:-$REMOTE_DIR/.venv/bin/python}"

# Output colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
info() { echo -e "${YELLOW}…${NC} $1"; }

# Python sqlite3 helpers.
db_query() {
  python3 -c "
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1])
row = conn.execute(sys.argv[2]).fetchone()
conn.close()
print('' if row is None else row[0])
" "$DB_PATH" "$1"
}

db_tables() {
  python3 -c "
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1])
rows = conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\").fetchall()
conn.close()
print(' '.join(r[0] for r in rows))
" "$DB_PATH"
}

# Pre-flight
command -v python3 >/dev/null || fail "python3 not installed"
command -v curl >/dev/null || fail "curl not installed"
[ -x "$PYTHON_BIN" ] || fail "Python venv missing: $PYTHON_BIN (run uv sync)"

echo "Verifying ETF overseas pipeline (DB: $DB_PATH)"
echo ""

# --- 1. Daemon alive ---
info "1. Daemon process"
[ -f "$PIDFILE" ] || fail "No PID file at $PIDFILE (was start-fetcher.sh used?)"
PID=$(cat "$PIDFILE")
kill -0 "$PID" 2>/dev/null || fail "Daemon PID $PID is not alive"
pass "Daemon PID $PID is alive"

# --- 2. Local DB schema ---
info "2. Local DB schema"
[ -f "$DB_PATH" ] || fail "Local DB not found: $DB_PATH"
TABLES=$(db_tables) || fail "Cannot open local DB"
for t in etf_quote etf_fundamentals etf_news push_log fetch_log etf_dead_letter; do
  echo "$TABLES" | grep -qw "$t" || fail "Missing table: $t"
done
pass "Local DB has required tables"

# --- 3. /health on the daemon ---
info "3. Daemon /health endpoint (127.0.0.1:8001)"
HEALTH=$(curl -sf --max-time 5 "$HEALTH_URL") || fail "/health did not respond at $HEALTH_URL"
echo "$HEALTH" | python3 -m json.tool >/dev/null || fail "/health not valid JSON: $HEALTH"
HEALTH_STATUS=$(echo "$HEALTH" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status',''))")
[ "$HEALTH_STATUS" = "ok" ] || fail "/health not ok (status=$HEALTH_STATUS): $HEALTH"
pass "/health responds with status=ok"

# --- 4. Recent fetch activity ---
info "4. fetch_log has entries from the last hour"
FETCHES=$(db_query "SELECT COUNT(*) FROM fetch_log WHERE ts > datetime('now', '-1 hour')")
[ "$FETCHES" -gt 0 ] || fail "No fetch_log entries in the last hour — daemon may not be fetching"
pass "$FETCHES fetch_log entries in the last hour"

# --- 5. Recent push activity ---
info "5. push_log has successful entries from the last hour"
SUCCESSES=$(db_query "SELECT COUNT(*) FROM push_log WHERE http_status BETWEEN 200 AND 299 AND sent_at > datetime('now', '-1 hour')")
[ "$SUCCESSES" -gt 0 ] || fail "No successful pushes in the last hour"
pass "$SUCCESSES successful pushes in the last hour"

# --- 6. Manual one-shot push ---
info "6. Manual one-shot push (live HTTPS to domestic)"
cd "$SCRIPT_DIR"
PYTHONPATH="$SCRIPT_DIR" "$PYTHON_BIN" -c "
from remote_data.config import load_config
from remote_data.pusher import client, payload
cfg = load_config()
body = payload.build_body('etf_quote', [{
    'symbol': 'VERIFY', 'ts': '2026-07-02T03:30:00Z', 'price': 99.9,
}])
result = client.post_batch(cfg, body)
print(f'status={result.status_code} retries={result.retries}')
if result.status_code != 200:
    print(f'body={result.body[:200] if result.body else \"<empty>\"}')
    raise SystemExit(1)
" || fail "Manual one-shot push did not return 200"
pass "Manual push returned 200"

# --- 7. No recent 401 storms ---
info "7. No 401 storms in push_log (last hour)"
FAILS=$(db_query "SELECT COUNT(*) FROM push_log WHERE http_status = 401 AND sent_at > datetime('now', '-1 hour')")
[ "$FAILS" -lt 5 ] || fail "$FAILS 401s in the last hour — secret mismatch likely"
pass "401 count in last hour: $FAILS (expected <5)"

# --- 8. Domestic etf symbols visible ---
info "8. Domestic /api/etf/symbols has entries"
SYMS=$(curl -sf --max-time 15 "$DOMESTIC_BASE/api/etf/symbols" 2>/tmp/_dom_sym_err) || {
  echo "  curl stderr: $(cat /tmp/_dom_sym_err)"
  fail "Cannot fetch domestic symbols"
}
N=$(echo "$SYMS" | python3 -c "import json,sys; print(len(json.load(sys.stdin)['symbols']))")
[ "$N" -gt 0 ] || fail "Domestic symbol list is empty — no rows have landed yet"
pass "Domestic has $N symbol(s)"

# --- 9. Log has no ERROR lines in last 100 ---
info "9. No ERROR lines in recent log tail"
if [ -f "$LOG_FILE" ]; then
  ERRS=$(tail -100 "$LOG_FILE" | grep -c "ERROR" || true)
  [ "$ERRS" -lt 5 ] || fail "$ERRS ERROR lines in last 100 log lines"
  pass "ERROR count in last 100 lines: $ERRS"
else
  info "  (no log file at $LOG_FILE, skipping)"
fi

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  All overseas checks passed.${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"