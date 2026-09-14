#!/usr/bin/env python3
"""Call every tool the server exposes, once, in one stdio session.

Writes docs/tool-shapes.json: for each tool, the arguments used, whether the call
succeeded, and the *shape* of what came back (top-level keys, and the keys of the
first element of the data array). No prices or names are kept - the point is the
shape, which is stable, rather than the values, which are not.

This is how TOOLS.md gets its "what comes back" column without anybody guessing.

    PUNTERSEDGE_API_KEY=pe_... python3 tools/probe_all_tools.py -- puntersedge-mcp

Tools that need an argument get a sensible one below. A tool that still fails is
recorded with its error, not quietly dropped.
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_probe import StdioClient, extract_payload  # noqa: E402

# Arguments for the tools that need one. Everything else is called with {}.
ARGS = {
    "racing_next_to_go": {"country": "AU", "num_races": 2, "categories": "horse"},
    "racing_best_odds": {"country": "AU", "num_races": 1, "categories": "horse"},
    "racing_movers": {"country": "AU", "min_books": 2},
    "racing_events": {"country": "AU", "hours_ahead": 6},
    "racing_results": {"country": "AU", "limit": 3},
    "racing_track_conditions": {},
    "racing_acceptances": {},
    "racing_price_history": {},          # race_id filled in at runtime
    "racing_closing_lines": {"limit": 2},
    "racing_changes": {},                # `since` filled in at runtime
    "horse_form": {},                    # `horse` filled in at runtime
    "greyhound_form": {"limit": 3},      # `dog` filled in at runtime
    "greyhound_stats": {"by": "track"},  # `dog` filled in at runtime
    "jockey_stats": {"state": "NSW"},
    "trainer_stats": {"state": "NSW"},
    "sports_odds": {"sport_key": "afl", "markets": "h2h"},
    "best_odds": {"sport_key": "afl"},
    "arb_best_prices": {"sport_key": "afl"},
    "demo_best_odds": {"sport": "afl"},
}


def shape_of(value, depth=0):
    """Describe a decoded payload without keeping its values."""
    if isinstance(value, dict):
        out = {"type": "object", "keys": sorted(value.keys())}
        if depth == 0 and isinstance(value.get("data"), (list, dict)):
            out["data"] = shape_of(value["data"], depth + 1)
        return out
    if isinstance(value, list):
        out = {"type": "array", "length": len(value)}
        if value and isinstance(value[0], dict):
            out["first_item_keys"] = sorted(value[0].keys())
        elif value:
            out["first_item_type"] = type(value[0]).__name__
        return out
    return {"type": type(value).__name__}


def main():
    argv = [x for x in sys.argv[1:] if x != "--"]
    if not argv:
        argv = ["puntersedge-mcp"]

    c = StdioClient(argv, verbose=False, timeout=120)
    init = c.initialize(client_name="probe_all_tools")
    server = init.get("result", {}).get("serverInfo", {})
    tools = c.request("tools/list").get("result", {}).get("tools", [])

    def call(name, args):
        return extract_payload(c.request(
            "tools/call", {"name": name, "arguments": args}))

    # Three tools need a real-world identifier, and a stale hardcoded one rots:
    # a retired horse 404s, and a race carded minutes ago has no price history
    # yet. Resolve all of them from live data at run time.
    race_id = None
    try:
        res = call("racing_results", {"country": "AU", "limit": 10})
        ids = [r["race_id"] for r in (res.get("data") or []) if r.get("race_id")]
        race_id = ids[0] if ids else None
    except Exception:
        pass
    if race_id:
        ARGS["racing_price_history"] = {"race_id": race_id}

    for category, tools_needing in (("horse", ["horse_form"]),
                                    ("greyhound", ["greyhound_form",
                                                   "greyhound_stats"])):
        try:
            d = call("racing_next_to_go",
                     {"country": "AU", "num_races": 1, "categories": category})
            runner = (d.get("data") or [{}])[0].get("runners", [{}])[0].get("name")
        except Exception:
            runner = None
        if runner:
            field = "horse" if category == "horse" else "dog"
            for tname in tools_needing:
                ARGS[tname][field] = runner

    # racing_changes requires `since`; a five-minute window is a realistic poll.
    since = (datetime.datetime.now(datetime.timezone.utc)
             - datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ARGS["racing_changes"] = {"since": since, "country": "AU"}

    report = {
        "captured_at": datetime.datetime.now(datetime.timezone.utc)
                               .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "server_command": " ".join(argv),
        "server_name": server.get("name"),
        "server_version": server.get("version"),
        "key_present": bool(os.environ.get("PUNTERSEDGE_API_KEY")),
        "tool_count": len(tools),
        "race_id_used_for_price_history": race_id,
        "tools": {},
    }

    for t in sorted(tools, key=lambda x: x["name"]):
        name = t["name"]
        args = ARGS.get(name, {})
        entry = {"arguments": args}
        try:
            resp = c.request("tools/call", {"name": name, "arguments": args})
            payload = extract_payload(resp)
            entry["is_error_flag"] = resp.get("result", {}).get("isError")
            if entry["is_error_flag"]:
                # The MCP layer itself rejected the call (bad/missing argument).
                # Note that the API's own 4xx/5xx do NOT set this flag.
                entry["ok"] = False
                entry["error"] = "MCP-level error"
                entry["error_text"] = payload if isinstance(payload, str) else None
            elif isinstance(payload, dict) and "error" in payload:
                entry["ok"] = False
                entry["error"] = payload.get("error")
                entry["hint"] = payload.get("hint")
            else:
                entry["ok"] = True
                entry["shape"] = shape_of(payload)
                if isinstance(payload, dict):
                    entry["credits_cost"] = payload.get("credits_cost")
        except Exception as exc:
            entry["ok"] = False
            entry["error"] = "%s: %s" % (type(exc).__name__, exc)
        report["tools"][name] = entry
        print("%-30s %s" % (name, "ok" if entry.get("ok") else
                            "FAILED " + str(entry.get("error"))))

    c.close()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "docs", "tool-shapes.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump(report, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print("\nwrote %s" % os.path.normpath(out))


if __name__ == "__main__":
    main()
