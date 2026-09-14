#!/usr/bin/env bash
# Regenerate everything in transcripts/ by actually talking to the servers.
#
#   bash tools/capture_transcripts.sh
#   PUNTERSEDGE_API_KEY=pe_... bash tools/capture_transcripts.sh
#
# Without a key you get transcripts 01-05 (handshake, tool list, the two keyless
# demo tools, and the TypeScript server). With a key you get the rest.
#
# The Python server must be on PATH (pip install puntersedge-mcp), or set
# SERVER_PY to its full path. The TypeScript server is fetched by npx on demand.
set -u
cd "$(dirname "$0")/.."
T=transcripts
mkdir -p "$T"
PY=${PYTHON:-python3}
PROBE="$PY tools/mcp_probe.py"
SERVER_PY=${SERVER_PY:-puntersedge-mcp}

say() { printf '\n=== %s\n' "$1"; }

say "01 initialize handshake (Python server, no key)"
env -u PUNTERSEDGE_API_KEY $PROBE --timeout 60 -- $SERVER_PY > "$T/01-initialize-python.txt" 2>&1

say "02 tools/list (Python server, no key) - full tool schemas"
env -u PUNTERSEDGE_API_KEY $PROBE --list --timeout 60 -- $SERVER_PY > "$T/02-tools-list-python.txt" 2>&1

say "03 demo_next_to_go (no key)"
env -u PUNTERSEDGE_API_KEY $PROBE --call demo_next_to_go --truncate 1400 --timeout 60 \
  -- $SERVER_PY > "$T/03-demo-next-to-go-nokey.txt" 2>&1

say "04 demo_best_odds (no key)"
env -u PUNTERSEDGE_API_KEY $PROBE --call demo_best_odds --args '{"sport":"afl"}' \
  --truncate 1400 --timeout 60 -- $SERVER_PY > "$T/04-demo-best-odds-nokey.txt" 2>&1

say "05 initialize + tools/list (TypeScript server via npx)"
env -u PUNTERSEDGE_API_KEY $PROBE --list --truncate 1400 --timeout 300 \
  -- npx -y github:Propertyscout001/puntersedge-mcp > "$T/05-typescript-server.txt" 2>&1

if [ -z "${PUNTERSEDGE_API_KEY:-}" ]; then
  echo
  echo "PUNTERSEDGE_API_KEY not set - stopping after the keyless transcripts."
  exit 0
fi

say "06 racing_next_to_go with country=AU (keyed)"
$PROBE --call racing_next_to_go --args '{"country":"AU","num_races":2,"categories":"horse"}' \
  --truncate 1800 --timeout 120 -- $SERVER_PY > "$T/06-racing-next-to-go-keyed.txt" 2>&1

say "07 racing_movers WITHOUT a country filter (keyed)"
$PROBE --call racing_movers --args '{"min_books":2}' \
  --truncate 1600 --timeout 120 -- $SERVER_PY > "$T/07-racing-movers-no-country-keyed.txt" 2>&1

say "08 racing_movers WITH country=AU, same moment (keyed)"
$PROBE --call racing_movers --args '{"country":"AU","min_books":2}' \
  --truncate 1600 --timeout 120 -- $SERVER_PY > "$T/08-racing-movers-country-au-keyed.txt" 2>&1

say "09 racing_best_odds (keyed)"
$PROBE --call racing_best_odds --args '{"country":"AU","num_races":1,"categories":"horse"}' \
  --truncate 1800 --timeout 120 -- $SERVER_PY > "$T/09-racing-best-odds-keyed.txt" 2>&1

say "10 racing_price_history (keyed) - race_id resolved from a settled race first"
RACE_ID=$($PROBE --call racing_results --args '{"country":"AU","limit":10}' --extract \
  --timeout 120 -- $SERVER_PY | $PY -c '
import json, sys
d = json.load(sys.stdin)
rows = d.get("data") or []
# race_id is null on some results rows - take the first row that has one.
ids = [r["race_id"] for r in rows if r.get("race_id")]
print(ids[0] if ids else "")')
if [ -n "$RACE_ID" ]; then
  echo "    using race_id=$RACE_ID"
  $PROBE --call racing_price_history --args "{\"race_id\":\"$RACE_ID\"}" \
    --truncate 1800 --timeout 120 -- $SERVER_PY > "$T/10-racing-price-history-keyed.txt" 2>&1
else
  echo "    no settled race with a race_id right now - skipped"
fi

say "11 connector_health (keyed, free)"
$PROBE --call connector_health --truncate 2200 --timeout 120 \
  -- $SERVER_PY > "$T/11-connector-health-keyed.txt" 2>&1

say "12 list_sports (keyed)"
$PROBE --call list_sports --truncate 1800 --timeout 60 \
  -- $SERVER_PY > "$T/12-list-sports-keyed.txt" 2>&1

say "13 check_usage (keyed, free)"
$PROBE --call check_usage --truncate 1200 --timeout 60 \
  -- $SERVER_PY > "$T/13-check-usage-keyed.txt" 2>&1

say "14 an intentionally bad argument, to show the error shape"
$PROBE --call racing_movers --args '{"direction":"steam"}' --truncate 1200 --timeout 60 \
  -- $SERVER_PY > "$T/14-error-bad-argument-keyed.txt" 2>&1

echo
echo "done. transcripts/ rewritten."
