#!/bin/bash

# Verify the ETF remote-data-persist side (domestic) is healthy.
#
# Run from the domestic box (or any box that can reach https://www.51stock.com.cn).
# Exits 0 on success, non-zero on any check failure.
#
# Uses Python's stdlib `sqlite3` — no external CLI needed.

set -e

# Locate repo so we can read .env
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

# Configurable via env (defaults match the standard deploy)
API_BASE="${API_BASE:-https://www.51stock.com.cn}"
DB_PATH="${DB_PATH:-$BACKEND_DIR/data/etf_remote.db}"
ENV_FILE="${ENV_FILE:-$BACKEND_DIR/.env}"

# Output colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'

pass() { echo -e "${GREEN}✓${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; exit 1; }
info() { echo -e "${YELLOW}…${NC} $1"; }

# Python sqlite3 helpers — single source of truth for DB queries.
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
[ -f "$ENV_FILE" ] || fail "Env file not found: $ENV_FILE"
SECRET=$(grep '^ETF_PIPELINE_SECRET=' "$ENV_FILE" | cut -d= -f2- | tr -d '\n\r')
[ -n "$SECRET" ] || fail "ETF_PIPELINE_SECRET is empty in $ENV_FILE"
[ -f "$DB_PATH" ] || fail "DB not found: $DB_PATH (has the backend started at least once?)"
command -v python3 >/dev/null || fail "python3 not installed"
command -v curl >/dev/null || fail "curl not installed"

echo "Verifying ETF domestic pipeline (API: $API_BASE, DB: $DB_PATH)"
echo ""

# --- 1. Schema ---
info "1. Schema check (10 tables + indexes)"
TABLES=$(db_tables) || fail "Cannot open DB"
for t in etf_quote etf_fundamentals etf_holdings etf_sector_weights \
         etf_performance etf_equity_holdings etf_esg etf_news \
         etf_ingest_log rate_limit_state; do
  echo "$TABLES" | grep -qw "$t" || fail "Missing table: $t"
done
pass "All 10 tables present"

# --- 2. Symbols endpoint ---
info "2. /api/etf/symbols"
SYMS=$(curl -sf --max-time 10 "$API_BASE/api/etf/symbols") || fail "/api/etf/symbols failed"
echo "$SYMS" | python3 -m json.tool >/dev/null || fail "/symbols malformed"
pass "/symbols responds"

# --- 3. Ingest (parse + persist round-trip) ---
info "3. POST /api/etf/ingest with valid signature"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
RUN_ID=$(date +%s | tail -c 6)
SYMBOL="VFY${RUN_ID}"
BODY=$(printf '{"data_type":"etf_quote","batch_id":"verify-%s","records":[{"symbol":"%s","ts":"%s","price":42.5}]}' \
       "$RUN_ID" "$SYMBOL" "$TS")
SIG=$(python3 -c "import hmac,hashlib,sys; print(hmac.new(sys.argv[1].encode(), sys.argv[2].encode()+b'\n'+sys.argv[3].encode(), hashlib.sha256).hexdigest())" \
       "$SECRET" "$TS" "$BODY")
RESP=$(curl -sf --max-time 10 -X POST "$API_BASE/api/etf/ingest" \
  -H "Content-Type: application/json" \
  -H "X-ETF-Pipeline-Timestamp: $TS" \
  -H "X-ETF-Pipeline-Signature: $SIG" \
  -d "$BODY") || fail "Ingest POST failed"
echo "$RESP" | grep -q '"accepted":1' || fail "Ingest did not accept: $RESP"
pass "Ingest accepted 1 record ($SYMBOL)"

# --- 4. Round-trip read ---
info "4. Read back via /api/etf/quote/{symbol}"
sleep 1
QUOTE=$(curl -sf --max-time 10 "$API_BASE/api/etf/quote/$SYMBOL") || fail "Quote read failed for $SYMBOL"
echo "$QUOTE" | grep -q "$SYMBOL" || fail "Quote response missing $SYMBOL"
echo "$QUOTE" | grep -q '42.5' || fail "Price 42.5 not persisted"
pass "Round-trip successful"

# --- 5. Bad signature → 401 ---
info "5. Bad signature must return 401"
HTTP=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 -X POST "$API_BASE/api/etf/ingest" \
  -H "Content-Type: application/json" \
  -H "X-ETF-Pipeline-Timestamp: $TS" \
  -H "X-ETF-Pipeline-Signature: deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef" \
  -d "$BODY")
[ "$HTTP" = "401" ] || fail "Bad sig should be 401, got $HTTP"
pass "Bad signature rejected with 401"

# --- 6. 404 on missing symbol ---
info "6. /api/etf/quote/UNKNOWN returns 404"
HTTP=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$API_BASE/api/etf/quote/QQQX")
[ "$HTTP" = "404" ] || fail "Missing symbol should be 404, got $HTTP"
pass "Missing data returns 404"

# --- 7. Audit log written ---
info "7. /api/etf/ingest writes to etf_ingest_log"
COUNT=$(db_query "SELECT COUNT(*) FROM etf_ingest_log WHERE batch_id = 'verify-$RUN_ID'")
[ "$COUNT" = "1" ] || fail "Expected 1 audit row, got $COUNT"
pass "Audit row written"

# --- 8. No audit row for the 401 ---
info "8. 401 must NOT write an audit row"
PRE=$(db_query "SELECT COUNT(*) FROM etf_ingest_log")
HTTP=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 -X POST "$API_BASE/api/etf/ingest" \
  -H "Content-Type: application/json" \
  -H "X-ETF-Pipeline-Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -H "X-ETF-Pipeline-Signature: deadbeef" \
  -d "$BODY")
POST=$(db_query "SELECT COUNT(*) FROM etf_ingest_log")
[ "$HTTP" = "401" ] || fail "Bad sig should be 401, got $HTTP"
[ "$PRE" = "$POST" ] || fail "Audit log grew on 401 ($PRE → $POST) — HMAC failure should be silent"
pass "401 leaves audit log untouched"

# --- 9. Rate limit table populated ---
info "9. rate_limit_state reachable"
RL=$(db_query "SELECT COUNT(*) FROM rate_limit_state")
pass "rate_limit_state reachable ($RL rows)"

# Cleanup: remove the verify rows so they don't pollute the read API
info "Cleanup: removing verify rows"
python3 -c "
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1])
conn.execute(\"DELETE FROM etf_quote WHERE symbol = ?\", ('$SYMBOL',))
conn.execute(\"DELETE FROM etf_ingest_log WHERE batch_id = ?\", ('verify-$RUN_ID',))
conn.commit()
conn.close()
" "$DB_PATH" >/dev/null
pass "Cleanup done"

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  All domestic checks passed.${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"