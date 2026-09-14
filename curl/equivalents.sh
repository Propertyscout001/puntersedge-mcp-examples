#!/usr/bin/env bash
# The HTTP call behind every MCP tool, as a curl you can paste.
#
# The MCP servers are a typed wrapper over the same REST API. If you are not
# running an assistant - or you are debugging one and want to know what it
# actually asked for - this is the same request without the protocol.
#
#   bash curl/equivalents.sh --list                 # the whole mapping
#   bash curl/equivalents.sh demo_next_to_go        # keyless, runs immediately
#   PE_API_KEY=pe_... bash curl/equivalents.sh racing_next_to_go
#
# Reads the key from PE_API_KEY, or PUNTERSEDGE_API_KEY if that is what you
# already have set for the MCP server. Never hardcode it.
set -u
BASE="https://api.puntersedge.online/v1"
KEY="${PE_API_KEY:-${PUNTERSEDGE_API_KEY:-}}"

# tool_name|path and query|needs a key?
MAP='
demo_next_to_go|/demo/racing/next-to-go|no
demo_best_odds|/demo/best-odds?sport=afl|no
racing_next_to_go|/racing/next-to-go?country=AU&num_races=3&categories=horse|yes
racing_best_odds|/racing/best-odds?country=AU&num_races=1&categories=horse|yes
racing_movers|/racing/movers?country=AU&min_books=2|yes
racing_changes|/racing/changes?country=AU&since=2026-09-15T00:00:00Z|yes
racing_events|/racing/events?country=AU&hours_ahead=6|yes
racing_track_conditions|/racing/track-conditions|yes
racing_acceptances|/racing/acceptances|yes
racing_venues|/racing/venues|yes
racing_results|/racing/results?country=AU&limit=5|yes
racing_results_coverage|/racing/results/coverage|yes
racing_price_history|/racing/price-history?race_id=REPLACE_WITH_RACE_ID|yes
racing_closing_lines|/racing/closing-lines?limit=5|yes
racing_closing_lines_coverage|/racing/closing-lines/coverage|yes
horse_form|/racing/horses/form?horse=REPLACE_WITH_HORSE_NAME|yes
greyhound_form|/racing/greyhounds/form?dog=REPLACE_WITH_DOG_NAME&limit=5|yes
greyhound_stats|/racing/greyhounds/stats?dog=REPLACE_WITH_DOG_NAME&by=track|yes
jockey_stats|/racing/jockeys/stats?state=NSW|yes
trainer_stats|/racing/trainers/stats?state=NSW|yes
list_sports|/sports|yes
sports_odds|/sports/afl/odds?markets=h2h|yes
best_odds|/best-odds/afl|yes
arb_best_prices|/arb/best-prices?sport_key=afl|yes
check_usage|/usage|yes
connector_health|/health|yes
'

list() {
  printf '%-30s %-6s %s\n' "MCP TOOL" "KEY?" "HTTP"
  printf '%-30s %-6s %s\n' "------------------------------" "------" "----"
  echo "$MAP" | while IFS='|' read -r tool path needs; do
    [ -z "$tool" ] && continue
    printf '%-30s %-6s GET %s%s\n' "$tool" "$needs" "$BASE" "$path"
  done
}

case "${1:-}" in
  ""|--list|-l|--help|-h) list; exit 0 ;;
esac

line=$(echo "$MAP" | grep "^$1|" || true)
if [ -z "$line" ]; then
  echo "unknown tool: $1" >&2
  echo "run: bash curl/equivalents.sh --list" >&2
  exit 2
fi
path=$(echo "$line" | cut -d'|' -f2)
needs=$(echo "$line" | cut -d'|' -f3)
url="$BASE$path"

echo "# $1"
if [ "$needs" = "no" ]; then
  echo "curl -s --compressed '$url'"
  echo
  curl -s --compressed -H 'Accept-Encoding: gzip' "$url"
  echo
  exit 0
fi

echo "curl -s --compressed -H \"X-API-Key: \$PE_API_KEY\" '$url'"
echo
if [ -z "$KEY" ]; then
  echo "(PE_API_KEY not set, so nothing was sent. Free key, no card:" >&2
  echo " https://puntersedge.online/api?utm_source=puntersedge-mcp-examples&utm_medium=code)" >&2
  exit 1
fi
case "$url" in
  *REPLACE_WITH_*)
    echo "(this one needs an identifier - edit the URL above first)" >&2
    exit 1 ;;
esac
# -D - prints the response headers, where X-Credits-Used and X-Credits-Remaining live.
curl -s --compressed -D - -H "X-API-Key: $KEY" -H 'Accept-Encoding: gzip' "$url"
echo
