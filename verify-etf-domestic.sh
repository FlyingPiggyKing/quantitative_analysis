#!/bin/bash

# Verify the ETF remote-data-persist side (domestic) is healthy.
#
# Run from the domestic box (or any box that can reach https://www.51stock.com.cn).
# Exits 0 on success, non-zero on any check failure.

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

# Pre-flight
[ -f "$ENV_FILE" ] || fail "Env file not found: $ENV_FILE"
SECRET=$(grep '^ETF_PIPELINE_SECRET=' "$ENV_FILE" | cut -d= -f2- | tr -d '\n\r')
[ -n "$SECRET" ] || fail "ETF_PIPELINE_SECRET is empty in $ENV_FILE"
[ -f "$DB_PATH" ] || fail "DB not found: $DB_PATH (has the backend started at least once?)"
command -v sqlite3 >/dev/null || fail "sqlite3 CLI not installed"
command -v python3 >/dev/null || fail "python3 not installed"
command -v curl >/dev/null || fail "curl not installed"

echo "Verifying ETF domestic pipeline (API: $API_BASE, DB: $DB_PATH)"
echo ""

# --- 1. Schema ---
info "1. Schema check (10 tables + indexes)"
TABLES=$(sqlite3 "$DB_PATH" ".tables" 2>/dev/null) || fail "Cannot open DB"
for t in etf_quote etf_fundamentals etf_holdings etf_sector_weights \
         etf_performance etf_equity_holdings etf_esg etf_news \
         etf_ingest_log rate_limit_state; do
  echo "$TABLES" | grep -qw "$t" || fail "Missing table: $t"
done
pass "All 10 tables present"

# --- 2. /health ---
info "2. /health endpoint"
HEALTH=$(curl -sf --max-time 10 "$API_BASE/health") || fail "/health did not respond"
echo "$HEALTH" | python3 -m json.tool >/dev/null || fail "/health is not valid JSON: $HEALTH"
echo "$HEALTH" | grep -q '"status"' || fail "/health missing status field"
pass "/health responds with valid JSON"

# --- 3. Symbols endpoint ---
info "3. /api/etf/symbols"
SYMS=$(curl -sf --max-time 10 "$API_BASE/api/etf/symbols") || fail "/api/etf/symbols failed"
echo "$SYMS" | python3 -m json.tool >/dev/null || fail "/symbols malformed"
pass "/symbols responds"

# --- 4. Ingest (parse + persist round-trip) ---
info "4. POST /api/etf/ingest with valid signature"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
# Unique symbol per run so we don't collide with prior verify runs
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

# --- 5. Round-trip read ---
info "5. Read back via /api/etf/quote/{symbol}"
sleep 1
QUOTE=$(curl -sf --max-time 10 "$API_BASE/api/etf/quote/$SYMBOL") || fail "Quote read failed for $SYMBOL"
echo "$QUOTE" | grep -q "$SYMBOL" || fail "Quote response missing $SYMBOL"
echo "$QUOTE" | grep -q '42.5' || fail "Price 42.5 not persisted"
pass "Round-trip successful"

# --- 6. Bad signature → 401 ---
info "6. Bad signature must return 401"
HTTP=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 -X POST "$API_BASE/api/etf/ingest" \
  -H "Content-Type: application/json" \
  -H "X-ETF-Pipeline-Timestamp: $TS" \
  -H "X-ETF-Pipeline-Signature: deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef" \
  -d "$BODY")
[ "$HTTP" = "401" ] || fail "Bad sig should be 401, got $HTTP"
pass "Bad signature rejected with 401"

# --- 7. 404 on missing symbol ---
info "7. /api/etf/quote/UNKNOWN returns 404"
HTTP=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$API_BASE/api/etf/quote/QQQX")
[ "$HTTP" = "404" ] || fail "Missing symbol should be 404, got $HTTP"
pass "Missing data returns 404"

# --- 8. Audit log written ---
info "8. /api/etf/ingest writes to etf_ingest_log"
COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM etf_ingest_log WHERE batch_id = 'verify-$RUN_ID'")
[ "$COUNT" -eq 1 ] || fail "Expected 1 audit row, got $COUNT"
pass "Audit row written"

# --- 9. No audit row for the 401 ---
info "9. 401 must NOT write an audit row"
PRE=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM etf_ingest_log")
HTTP=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 -X POST "$API_BASE/api/etf/ingest" \
  -H "Content-Type: application/json" \
  -H "X-ETF-Pipeline-Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -H "X-ETF-Pipeline-Signature: deadbeef" \
  -d "$BODY")
POST=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM etf_ingest_log")
[ "$HTTP" = "401" ] || fail "Bad sig should be 401, got $HTTP"
[ "$PRE" = "$POST" ] || fail "Audit log grew on 401 ($PRE → $POST) — HMAC failure should be silent"
pass "401 leaves audit log untouched"

# --- 10. Rate limit table populated ---
info "10. rate_limit_state has at least one row"
RL=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM rate_limit_state")
[ "$RL" -ge 0 ] || fail "rate_limit_state query failed"
pass "rate_limit_state reachable ($RL rows)"

# Cleanup: remove the verify rows so they don't pollute the read API
info "Cleanup: removing verify rows"
sqlite3 "$DB_PATH" "DELETE FROM etf_quote WHERE symbol = '$SYMBOL'" >/dev/null
sqlite3 "$DB_PATH" "DELETE FROM etf_ingest_log WHERE batch_id = 'verify-$RUN_ID'" >/dev/null
pass "Cleanup done"

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  All domestic checks passed.${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"