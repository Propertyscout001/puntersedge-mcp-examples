# Australian racing and sports odds over MCP: worked examples for Claude, Cursor and other MCP clients

PuntersEdge is an Australian odds API — thoroughbred, harness and greyhound
racing in Australia, thoroughbred and harness in New Zealand, plus Australian
sports (AFL, NRL, NBA, tennis, cricket and the rest) — and it ships two Model
Context Protocol servers so an assistant can read that data directly. This repo
is the part the server docs do not cover: config blocks that work per client, a
tool reference generated from the server's own `tools/list` reply, raw JSON-RPC
transcripts of real calls, and the plain `curl` equivalent of every tool for
anyone not running an assistant at all.

Nothing here places a bet or holds bookmaker credentials. It reads a data feed.

## Run it without an API key

Two of the tools are a no-key sandbox. This clones the repo, installs the
server, and has it answer a real call:

```sh
git clone https://github.com/Propertyscout001/puntersedge-mcp-examples
cd puntersedge-mcp-examples
python3 -m pip install puntersedge-mcp          # Python 3.10 or newer
python3 tools/mcp_probe.py --call demo_next_to_go -- puntersedge-mcp
```

`tools/mcp_probe.py` is a dependency-free MCP stdio client, 266 lines of
standard library. It does what Claude Desktop does — spawn the server, send
`initialize`, send `tools/call` — and prints every JSON-RPC frame verbatim, so
you can see exactly what an assistant would see.

If you would rather install nothing, the TypeScript server runs straight from
GitHub, and handshake plus tool list needs no key either:

```sh
python3 tools/mcp_probe.py --list --names-only -- npx -y github:Propertyscout001/puntersedge-mcp
```

## Real output

Captured 15 September 2026 (AEST) on this machine. Full file:
[`docs/output.txt`](docs/output.txt).

```
$ python3 tools/mcp_probe.py --list --names-only -- puntersedge-mcp

# mcp_probe 2026-09-15T09:30:15+1000
# server: puntersedge-mcp
# protocolVersion offered: 2025-06-18
# key present in env: no

initialize ok: puntersedge  (protocol 2025-06-18)

26 tools:
  racing_next_to_go            Next Australian/NZ races to jump, with runners and live per-bookmaker prices.     COST: 2 credit
  racing_best_odds             Best win, place and tote price per runner across every bookmaker, with the book     offering it 
  racing_movers                Consensus firmers and drifters in the live racing window. COST: 3 credits.     direction must be
  [20 tool lines elided - the full list is in docs/output.txt]
  arb_best_prices              Cross-book price comparison per selection, with every bookmaker's quote alongside     the best. 
  check_usage                  Current key's plan, monthly credit allowance, credits used and reset date.     COST: free. You r
  connector_health             Per-bookmaker feed freshness: last_ok, status, records written. COST: free.     THIS IS HOW YOU 
  demo_next_to_go              Free no-key sandbox sample of racing_next_to_go (3 races, 5 runners, 3 books,     truncated). CO
  demo_best_odds               Free no-key sandbox sample of sports best-odds with arb detection. COST: free.     `sport` is op

```

And the keyless tool call, protocol frames included:

```
$ python3 tools/mcp_probe.py --call demo_next_to_go --truncate 400 -- puntersedge-mcp

--> {
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "demo_next_to_go",
    "arguments": {}
  }
}

<-- {
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "text": "{\"data\": {\"demo\": true, \"note\": \"Free sandbox sample (truncated). Get a free API key for full data: https://puntersedge.online/api?utm_source=demo_api&utm_medium=sandbox\", \"signup_url\": \"https://puntersedge.online/api?utm_source=demo_api&utm_medium=sandbox\", \"shape\": \"Sandbox teaser: 3 races, 5 runners, best 3 prices, wrapped in this envelope. GET /v1/racing/next-to-go returns a bare array of full  <<< clipped by mcp_probe --truncate 400; full body was 7659 chars >>>",
        "type": "text"
      }
    ],
    "isError": false,
    ... structuredContent repeats the same string ...
  }
}
```

Fourteen transcripts, all captured the same way, are in
[`transcripts/`](transcripts/). They are raw protocol, not chat: request frame,
response frame, nothing rewritten. The bodies of the long ones are clipped at a
marked character count by `--truncate`; the framing is never touched.

## Which server is which

There are two official servers with the same name and different tool surfaces.
Both were run and handshaken for this repo on 15 September 2026.

| | Python | TypeScript |
|---|---|---|
| Install | `pip install puntersedge-mcp` ([PyPI](https://pypi.org/project/puntersedge-mcp/), 0.2.1) | `npx -y github:Propertyscout001/puntersedge-mcp` ([repo](https://github.com/Propertyscout001/puntersedge-mcp)) |
| Command in your config | `puntersedge-mcp` | `npx`, args `["-y", "github:Propertyscout001/puntersedge-mcp"]` |
| Tools | 26 | 9 |
| Reports itself as | `puntersedge`, version `""` | `puntersedge`, version `0.1.0` |
| Has the no-key demo tools | yes (`demo_next_to_go`, `demo_best_odds`) | no |
| Needs | Python 3.10+ | Node |
| Docs | [/developers/mcp-server](https://puntersedge.online/developers/mcp-server?utm_source=puntersedge-mcp-examples&utm_medium=readme) | no docs page of its own; its [repo](https://github.com/Propertyscout001/puntersedge-mcp) is the source of truth |

**There is no npm package called `puntersedge-mcp`.** `npm install -g
puntersedge-mcp` fails — `https://registry.npmjs.org/puntersedge-mcp` returns
404, checked 15 September 2026. The TypeScript server is installed from GitHub
by `npx`, exactly as written above. (The npm package `puntersedge` is a
different thing: the plain HTTP SDK.)

The Python server is the one to reach for unless you specifically want to avoid
a Python dependency. It has the demo tools, the form and premiership tools, the
change feed and the closing-line archive; the TypeScript one has the nine
core tools.

## Configure your client

Complete config files for each client are in [`configs/`](configs/), with the
file path each one belongs at. The short version — every stdio host takes the
same three facts, a command, arguments and an `env` block:

```json
{
  "mcpServers": {
    "puntersedge": {
      "command": "puntersedge-mcp",
      "env": { "PUNTERSEDGE_API_KEY": "PUT-YOUR-KEY-HERE" }
    }
  }
}
```

- **Claude Desktop** — `~/Library/Application Support/Claude/claude_desktop_config.json`
  (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows), then restart.
- **Claude Code** — `claude mcp add puntersedge -e PUNTERSEDGE_API_KEY=your-key-here -- puntersedge-mcp`.
  The CLI's default scope is `local`, which needs no approval step. `--scope project`
  writes `.mcp.json` into the repo and leaves the server *pending approval* until
  someone runs `claude` interactively — verified here, and it surprises people.
- **Cursor** — `.cursor/mcp.json` in the project, or `~/.cursor/mcp.json` globally.
- **Anything else** — the same JSON, wherever it keeps its server list.

The server reads the key from `PUNTERSEDGE_API_KEY` once at start-up. Drop the
`env` block and export it in the shell instead if you would rather it were not
in a file.

## With a free key

The free tier is 1,500 credits a month, no credit card:
[puntersedge.online/api](https://puntersedge.online/api?utm_source=puntersedge-mcp-examples&utm_medium=readme).

With a key set, the other 24 tools answer. Costs, per call, in credits:

| Free | 1 | 2 | 3 | 5 |
|---|---|---|---|---|
| `check_usage`, `connector_health`, both `demo_*` | `racing_events`, `racing_venues`, `racing_track_conditions`, `racing_results_coverage`, `racing_closing_lines_coverage`, `list_sports` | `racing_next_to_go`, `racing_results`, `racing_changes`, `racing_acceptances`, `jockey_stats`, `trainer_stats`, `arb_best_prices` | `racing_best_odds`, `racing_movers`, `horse_form`, `greyhound_form`, `greyhound_stats`, `best_odds` | `racing_price_history`, `racing_closing_lines` |

`sports_odds` is one credit per market requested, so `markets=h2h` is 1 and
`markets=h2h,spreads,totals` is 3. Every priced result comes back wrapped as
`{"data": ..., "credits_cost": "2", "credits_remaining": "1483"}`, so an
assistant can see its balance without spending a call to ask.

Then regenerate every keyed transcript yourself:

```sh
PUNTERSEDGE_API_KEY=your-key-here bash tools/capture_transcripts.sh
```

[`TOOLS.md`](TOOLS.md) is the per-tool reference: cost, HTTP endpoint,
parameters, a prompt that reaches it, and the keys that actually came back when
we called it. It is generated by `tools/gen_tools_md.py` from the server's own
`tools/list` reply plus [`docs/tool-shapes.json`](docs/tool-shapes.json), which
`tools/probe_all_tools.py` writes by calling all 26 tools in one session. Nobody
types that table by hand, so it cannot quietly drift from the server.
[`docs/tool-map.html`](docs/tool-map.html) is the same reference as a single
self-contained page, filterable, no CDN and no build step - open the file.

## What is in here

```
README.md                    this
TOOLS.md                     per-tool reference, generated
configs/                     ready-to-paste config per client, and where each file lives
transcripts/                 14 raw JSON-RPC captures, keyless and keyed
curl/equivalents.sh          the HTTP call behind every tool; prints it, and runs it
tools/mcp_probe.py           dependency-free MCP stdio client (the thing that made the captures)
tools/probe_all_tools.py     calls every tool once, records response shapes
tools/capture_transcripts.sh regenerates transcripts/
tools/capture_output.sh      regenerates docs/output.txt
tools/gen_tools_md.py        regenerates TOOLS.md
tools/gen_tool_map_html.py   regenerates docs/tool-map.html
docs/output.txt              captured terminal output, dated
docs/tool-shapes.json        what each tool returned, machine-readable
docs/tool-map.html           the tool reference as a page
```

## No assistant? The curl underneath

The servers are a typed wrapper over the same REST API. `curl/equivalents.sh`
prints — and runs — the HTTP call behind each tool:

```sh
bash curl/equivalents.sh --list             # the whole mapping
bash curl/equivalents.sh demo_next_to_go    # keyless, runs immediately
PE_API_KEY=pe_... bash curl/equivalents.sh racing_next_to_go
```

The keyed path prints response headers too, which is where `X-Credits-Cost`,
`X-Credits-Remaining` and the per-minute rate-limit counters live.

## How it works, and what we hit

`mcp_probe.py` speaks newline-delimited JSON-RPC 2.0 on the server's stdin and
stdout, offers `protocolVersion` `2025-06-18`, sends
`notifications/initialized`, then issues `tools/list` or `tools/call`. Server
logs on stderr are drained on a thread and printed after, so they cannot
interleave into the protocol stream. That is the whole transport.

Seven things that cost us time:

**The tool body is a JSON string, not an object.** The result is
`content[0].text`, and that text is itself JSON. You `json.loads` twice. The
server's own `outputSchema` says so — it declares `result` as `{"type":
"string"}`. `mcp_probe.py --extract` does the second decode for you.

**An API error arrives with `isError: false`.** A 422, a 429, a 500 — the tool
call still succeeds at the protocol level and the failure is inside the body as
`{"error": "HTTP 422", "detail": ..., "hint": ...}`. Only an MCP-level problem,
such as omitting `since` on `racing_changes`, sets `isError: true`. Branch on
the body, not the flag. Both shapes are captured in
[`transcripts/14-error-bad-argument-keyed.txt`](transcripts/14-error-bad-argument-keyed.txt).

**Racing is not AU-only, and the default is every country.** Asking
`racing_movers` for movers with no `country` returned three runners at Gavea,
`"country": "BR"` — Brazil, not Australia. Same moment, same `min_books`, with
`country: "AU"` added: an empty array, because no Australian market had moved
yet that morning. Both transcripts are in the repo,
[07](transcripts/07-racing-movers-no-country-keyed.txt) and
[08](transcripts/08-racing-movers-country-au-keyed.txt). Pass `country` on
`racing_next_to_go` and `racing_movers` or you will present Brazilian racing
under an Australian heading. The trade-off is real: a late-carded race whose
country has not resolved yet drops out of a filtered result.

**`racing_price_history` 404s on a race that has just been carded.** It returns
recorded ticks, and a race listed minutes ago has none. Eight consecutive
next-to-go races all 404'd; a race pulled from `racing_results` returned 100
points immediately. `tools/capture_transcripts.sh` resolves a settled `race_id`
first for exactly this reason — and `race_id` is `null` on some results rows, so
it takes the first row that has one.

**`connector_health` is `/v1/health`, not `/v1/health/connectors`.** Both exist.
The tool calls the first: a flat array of `connector`, `last_ok`, `last_poll`,
`status`, `records_written`. The second is the richer endpoint, with
`stale_after_s` and `any_stale`, and the tool does not expose it. Worth knowing
before an assistant reports a feed healthy.

**The tool surface is narrower than the HTTP surface.** `racing_movers` over
HTTP silently accepts and ignores unknown query parameters — we sent
`bogus_param=1` and got a normal 200 — while `racing_best_odds` refuses them
with a 422 naming the ones it does accept. The MCP tool schemas expose only the
parameters that are real, which is a good reason to use them over hand-rolled
HTTP.

**The demo tools are rate-limited at 30 calls a minute per IP.** Exceed it and you
get the same `isError: false` shape with `{"error": "HTTP 429", "hint": "Rate
limited. Wait 60 seconds and repeat the identical call."}` inside. We hit it while
capturing - section 7 of `docs/output.txt` is the moment it happened, and the
sweep three minutes later came back clean.

Two smaller things: send `Accept-Encoding: gzip` and reuse the connection if you
are calling the HTTP API directly — the responses compress heavily — and never
retry a price call silently, because a hidden retry can hand back a price
recorded before a move.

## Related

- [PuntersEdge MCP server docs](https://puntersedge.online/developers/mcp-server?utm_source=puntersedge-mcp-examples&utm_medium=readme) — the server's own page: install, tool table, notes it gives the assistant
- [Use the API from ChatGPT, Claude, Cursor and Copilot](https://puntersedge.online/developers/ai-assistants?utm_source=puntersedge-mcp-examples&utm_medium=readme) — the prompt-only route, for hosts that cannot run a local process
- [Getting started](https://puntersedge.online/developers/getting-started?utm_source=puntersedge-mcp-examples&utm_medium=readme) · [API reference](https://puntersedge.online/developers/api-reference?utm_source=puntersedge-mcp-examples&utm_medium=readme)
- [Coverage report](https://puntersedge.online/coverage-report?utm_source=puntersedge-mcp-examples&utm_medium=readme) — which bookmakers and codes are actually being served right now, measured rather than promised
- [TypeScript / JavaScript client](https://puntersedge.online/developers/typescript?utm_source=puntersedge-mcp-examples&utm_medium=readme) — the npm package `puntersedge`, which is the plain HTTP SDK and not an MCP server
- Sibling repos: [puntersedge-mcp](https://github.com/Propertyscout001/puntersedge-mcp) (the TypeScript server itself) · [puntersedge-python](https://github.com/Propertyscout001/puntersedge-python) · [puntersedge-node](https://github.com/Propertyscout001/puntersedge-node) · [puntersedge-examples](https://github.com/Propertyscout001/puntersedge-examples) · [au-racing-odds-dashboard](https://github.com/Propertyscout001/au-racing-odds-dashboard)

## Limitations

- **This repo is not the server.** It configures, drives and documents two
  servers that live elsewhere. Bugs in tool behaviour belong in their repos.
- **We ran the servers, not the clients.** Every handshake and tool call here
  was made by `tools/mcp_probe.py`, which is a faithful stdio client but is not
  Claude Desktop. The config files use each vendor's documented file location;
  the only one exercised end-to-end on this machine was Claude Code, where
  `claude mcp add --scope project` was run and `claude mcp list` reported the
  server as pending approval. Nothing was installed into Claude Desktop or
  Cursor here.
- **`check_usage` returned HTTP 500 for our key** at capture time —
  [`transcripts/13-check-usage-keyed.txt`](transcripts/13-check-usage-keyed.txt).
  It was captured with an internal unlimited build key, which is why
  `credits_remaining` reads `"unlimited"` in every keyed transcript instead of a
  number. We cannot say from here whether a normal free-tier key sees the same
  500; the transcript is kept because it shows the thing that matters, which is
  that a server-side failure still arrives as a normal tool result.
- **The transcripts are a moment, not a baseline.** Prices, race fields and
  which feeds are healthy all change. An empty `racing_movers` result at 09:19
  AEST says nothing about the rest of the day. Re-run
  `tools/capture_transcripts.sh` rather than trusting a committed number.
- **`racing_closing_lines` is plan-gated** and returns 403 on the free tier. Our
  build key is not on the free tier, so the shape recorded in `TOOLS.md` for
  that tool is not what a free-tier key will see. `racing_price_history` is the
  free-tier equivalent for market movement.
- **No prompts, no resources.** Both servers advertise `prompts` and `resources`
  capabilities with `listChanged: false`, and this repo does not exercise
  either — only `tools`.
- **`tools/probe_all_tools.py` calls every tool once.** On a free-tier key that
  is roughly 60 credits of your 1,500. It is not something to put on a timer.
- **No Windows testing.** Everything here was run on macOS with Python 3.12 for
  the server and system Python 3.9 for the probe. The probe is standard library
  and should be fine on 3.8+; the server needs 3.10+.

---
18+ only. Gambling can be addictive — please gamble responsibly.
Gambling Help: 1800 858 858 · https://www.gambleaware.nsw.gov.au
This repository is a developer example for reading an odds data feed. It is not betting
advice, it places no bets and it holds no bookmaker credentials.
