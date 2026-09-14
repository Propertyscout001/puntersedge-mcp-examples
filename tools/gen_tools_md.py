#!/usr/bin/env python3
"""Generate TOOLS.md from captured evidence, so the reference cannot drift.

Three inputs, all of them things that were actually observed:
  transcripts/02-tools-list-python.txt  - the server's own tools/list reply
  docs/tool-shapes.json                 - the response shape of every tool,
                                          recorded by tools/probe_all_tools.py
  the tables below                      - HTTP endpoint per tool, read out of
                                          puntersedge_mcp 0.2.1's source, and a
                                          hand-written example prompt per tool.

    python3 tools/gen_tools_md.py > TOOLS.md
"""

import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Tool -> HTTP endpoint. Read from puntersedge_mcp 0.2.1 server.py, then each one
# was called over HTTP to confirm it answers. Note connector_health: it calls
# /v1/health, the flat array, NOT /v1/health/connectors, which is a different
# (richer) endpoint carrying any_stale / stale_after_s.
ENDPOINT = {
    "racing_next_to_go": "GET /v1/racing/next-to-go",
    "racing_best_odds": "GET /v1/racing/best-odds",
    "racing_movers": "GET /v1/racing/movers",
    "racing_changes": "GET /v1/racing/changes",
    "racing_events": "GET /v1/racing/events",
    "racing_track_conditions": "GET /v1/racing/track-conditions",
    "racing_acceptances": "GET /v1/racing/acceptances",
    "racing_venues": "GET /v1/racing/venues",
    "racing_results": "GET /v1/racing/results",
    "racing_results_coverage": "GET /v1/racing/results/coverage",
    "racing_price_history": "GET /v1/racing/price-history",
    "racing_closing_lines": "GET /v1/racing/closing-lines",
    "racing_closing_lines_coverage": "GET /v1/racing/closing-lines/coverage",
    "horse_form": "GET /v1/racing/horses/form",
    "greyhound_form": "GET /v1/racing/greyhounds/form",
    "greyhound_stats": "GET /v1/racing/greyhounds/stats",
    "jockey_stats": "GET /v1/racing/jockeys/stats",
    "trainer_stats": "GET /v1/racing/trainers/stats",
    "list_sports": "GET /v1/sports",
    "sports_odds": "GET /v1/sports/{sport_key}/odds",
    "best_odds": "GET /v1/best-odds/{sport_key}",
    "arb_best_prices": "GET /v1/arb/best-prices",
    "check_usage": "GET /v1/usage",
    "connector_health": "GET /v1/health",
    "demo_next_to_go": "GET /v1/demo/racing/next-to-go",
    "demo_best_odds": "GET /v1/demo/best-odds",
}

# A prompt that reliably reaches the tool. Written by hand; the wording is the
# part a reader wants, so it is not generated.
PROMPT = {
    "racing_next_to_go": "What Australian horse races are jumping in the next half hour, and what is every bookmaker quoting on each runner?",
    "racing_best_odds": "For the next Australian thoroughbred race, which bookmaker has the best win price on each runner?",
    "racing_movers": "Which Australian runners have firmed across at least three bookmakers in the last hour?",
    "racing_changes": "Poll for Australian racing prices that changed in the last five minutes, and tell me what moved.",
    "racing_events": "List the Australian race meetings scheduled over the next six hours. I do not need prices.",
    "racing_track_conditions": "What is the track condition and rail position at Randwick today, and has it changed during the day?",
    "racing_acceptances": "Show me today's full acceptance card for Australian thoroughbred meetings.",
    "racing_venues": "List the Australian racing venues you cover and which codes run at each.",
    "racing_results": "What were the results and dividends for Australian races that ran in the last twelve hours?",
    "racing_results_coverage": "Before I report a missing result, tell me what results coverage actually is.",
    "racing_price_history": "Pull the recorded price ticks for race <race_id> and describe how the market moved.",
    "racing_closing_lines": "Pull the closing-line archive rows for yesterday's Randwick meeting.",
    "racing_closing_lines_coverage": "How far back does the closing-line archive go, and how much of it is resulted?",
    "horse_form": "What is the career record and recent form for the horse <name>?",
    "greyhound_form": "Show me the last five starts for the greyhound <name>.",
    "greyhound_stats": "Break down <dog>'s record by track, then by box.",
    "jockey_stats": "Who are the leading jockeys in NSW this season?",
    "trainer_stats": "Who are the leading trainers in Victoria this season?",
    "list_sports": "Which sports can I query, and what is each sport_key?",
    "sports_odds": "Get head-to-head odds for the upcoming AFL fixtures from every bookmaker you cover.",
    "best_odds": "For the next NRL round, which bookmaker has the best price on each team?",
    "arb_best_prices": "Compare every bookmaker's AFL head-to-head quote side by side with the best one.",
    "check_usage": "How many API credits have I used this month, and when does the allowance reset?",
    "connector_health": "Is any bookmaker feed stale right now? I want to know before I trust a quiet market.",
    "demo_next_to_go": "Show me the sandbox racing sample so I can see the response shape before I spend any credits.",
    "demo_best_odds": "Show me the sandbox AFL best-odds sample.",
}


def load_tools():
    path = os.path.join(ROOT, "transcripts", "02-tools-list-python.txt")
    txt = open(path).read()
    i = txt.index('"method": "tools/list"')
    rest = txt[i:]
    body = rest[rest.index("<-- ") + 4:]
    body = body[:body.rfind("\n}") + 2]
    return json.loads(body)["result"]["tools"]


def cost_of(description):
    m = re.search(r"COST:\s*([^.\n]+)", description or "")
    return m.group(1).strip() if m else "see description"


def first_sentence(description):
    d = " ".join((description or "").split())
    d = re.sub(r"\s*COST:.*$", "", d)
    return d.rstrip(". ") + "."


def shape_line(entry):
    if not entry:
        return "not called in this build"
    if not entry.get("ok"):
        return "the call failed when we ran it: `%s`" % entry.get("error")
    sh = entry.get("shape", {})
    keys = sh.get("keys") or []
    out = "`{%s}`" % ", ".join('"%s"' % k for k in keys)
    data = sh.get("data")
    if isinstance(data, dict):
        if data.get("type") == "array":
            fi = data.get("first_item_keys")
            out += "; `data` is an array"
            if fi:
                out += " whose items carry `%s`" % "`, `".join(fi)
        elif data.get("type") == "object":
            out += "; `data` is an object with `%s`" % "`, `".join(data.get("keys", []))
    return out


def main():
    tools = load_tools()
    shapes = json.load(open(os.path.join(ROOT, "docs", "tool-shapes.json")))
    st = shapes["tools"]

    w = sys.stdout.write
    w("# Tool reference: the PuntersEdge MCP servers\n\n")
    w("Generated by `tools/gen_tools_md.py` from three captured files, not from "
      "documentation. Re-run it after a server release and the table updates itself.\n\n")
    w("- tool names, descriptions and parameters: the server's own `tools/list` "
      "reply, in [`transcripts/02-tools-list-python.txt`](transcripts/02-tools-list-python.txt)\n")
    w("- response shapes: [`docs/tool-shapes.json`](docs/tool-shapes.json), written by "
      "`tools/probe_all_tools.py`, which calls every tool once and records the keys "
      "that came back\n")
    w("- HTTP endpoint per tool: read out of the `puntersedge-mcp` %s source and "
      "confirmed by calling each endpoint\n\n" % shapes.get("server_version_pypi", "0.2.1"))
    w("Server: `%s`, %d tools, swept %s.\n\n"
      % (shapes["server_command"], shapes["tool_count"], shapes["captured_at"]))
    w("Costs are in API credits and are the server's own figures, taken from each "
      "tool description. A malformed request is refused without being billed.\n\n")

    w("## At a glance\n\n")
    w("| Tool | Cost | HTTP endpoint |\n|---|---|---|\n")
    for t in tools:
        w("| [`%s`](#%s) | %s | `%s` |\n"
          % (t["name"], t["name"].replace("_", "-"), cost_of(t.get("description")),
             ENDPOINT.get(t["name"], "?")))
    w("\n")

    for t in tools:
        name = t["name"]
        w("## %s\n\n" % name)
        w("%s\n\n" % first_sentence(t.get("description")))
        w("- **Cost** %s\n" % cost_of(t.get("description")))
        w("- **HTTP** `%s`\n" % ENDPOINT.get(name, "?"))
        props = list((t.get("inputSchema") or {}).get("properties", {}).keys())
        req = (t.get("inputSchema") or {}).get("required", [])
        if props:
            w("- **Parameters** %s\n"
              % ", ".join("`%s`%s" % (p, " (required)" if p in req else "")
                          for p in props))
        else:
            w("- **Parameters** none\n")
        w("\n**Ask an assistant**\n\n> %s\n\n" % PROMPT.get(name, "-"))
        entry = st.get(name)
        w("**What came back** (%s, arguments `%s`)\n\n%s\n\n"
          % (shapes["captured_at"], json.dumps(entry.get("arguments", {})
                                               if entry else {}),
             shape_line(entry)))
        full = " ".join((t.get("description") or "").split())
        if full:
            w("<details><summary>The description the assistant sees</summary>\n\n"
              "```\n%s\n```\n\n</details>\n\n" % full)


if __name__ == "__main__":
    main()
