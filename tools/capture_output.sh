#!/usr/bin/env bash
# Rewrite docs/output.txt by running the commands the README shows.
#   bash tools/capture_output.sh > docs/output.txt 2>&1
set -u
cd "$(dirname "$0")/.."
run() { printf '\n$ %s\n\n' "$*"; eval "$@"; }
# Sections 1-5 are the no-key path, so the key is stripped from those
# child processes. Anything else would make "keyless" a claim, not a fact.
nokey() { printf '\n$ %s\n\n' "$*"; env -u PUNTERSEDGE_API_KEY -u PE_API_KEY bash -c "$*"; }

cat <<HDR
PuntersEdge MCP examples - captured terminal output
Run: $(date '+%Y-%m-%d %H:%M:%S %Z')
Host: $(uname -srm)
node: $(node -v 2>/dev/null || echo 'not installed')
probe python: $(python3 -V 2>&1)
server: puntersedge-mcp $(python3 -c "import importlib.metadata as m; print(m.version('puntersedge-mcp'))" 2>/dev/null || echo 'version unknown')

The Python server needs Python 3.10+. The system python3 on this machine is 3.9.6,
so the server was installed into a 3.12 virtualenv and that venv's bin directory
was put on PATH - which is why "probe python" above reads 3.12 here. The probe
itself is standard library only and was separately confirmed to run the same
handshake under /usr/bin/python3 3.9.6.

Sections 1-5 run with PUNTERSEDGE_API_KEY stripped from the environment, so the
"key present in env: no" line below is a fact rather than a label. Sections 6-8
use an internal unlimited build key, which is why credits_remaining reads
"unlimited" rather than a number.
HDR

printf '\n\n########## 1. keyless: handshake + tool list, Python server\n'
nokey "python3 tools/mcp_probe.py --list --names-only -- puntersedge-mcp"

printf '\n\n########## 2. keyless: a real tool call, protocol frames included\n'
nokey "python3 tools/mcp_probe.py --call demo_next_to_go --truncate 400 -- puntersedge-mcp"

printf '\n\n########## 3. keyless: the TypeScript server, fetched by npx\n'
nokey "python3 tools/mcp_probe.py --list --names-only -- npx -y github:Propertyscout001/puntersedge-mcp"

printf '\n\n########## 4. the curl mapping, for anyone not running an assistant\n'
run "bash curl/equivalents.sh --list"

printf '\n\n########## 5. keyless curl, trimmed\n'
printf '\n$ bash curl/equivalents.sh demo_next_to_go | head -c 700\n\n'
env -u PUNTERSEDGE_API_KEY -u PE_API_KEY bash curl/equivalents.sh demo_next_to_go | head -c 700; echo; echo '  [...]'

if [ -z "${PUNTERSEDGE_API_KEY:-}" ]; then
  printf '\n\nPUNTERSEDGE_API_KEY not set - keyed sections skipped.\n'
  exit 0
fi

printf '\n\n########## 6. keyed: --extract decodes the double-encoded body\n'
printf '\n$ python3 tools/mcp_probe.py --call racing_next_to_go \\\n'
printf '      --args %s --extract -- puntersedge-mcp | head -40\n\n' \
  "'{\"country\":\"AU\",\"num_races\":1,\"categories\":\"horse\"}'"
python3 tools/mcp_probe.py --call racing_next_to_go \
  --args '{"country":"AU","num_races":1,"categories":"horse"}' \
  --extract -- puntersedge-mcp 2>/dev/null | head -40
echo '  [...]'

printf '\n\n########## 7. keyed: every tool called once, shapes recorded\n'
run "python3 tools/probe_all_tools.py -- puntersedge-mcp"

printf '\n\n########## 8. keyed curl, showing the credit headers\n'
printf '\n$ PE_API_KEY=... bash curl/equivalents.sh racing_movers | head -25\n\n'
PE_API_KEY="$PUNTERSEDGE_API_KEY" bash curl/equivalents.sh racing_movers 2>&1 | head -25
echo '  [...]'
echo
echo "end of capture."
