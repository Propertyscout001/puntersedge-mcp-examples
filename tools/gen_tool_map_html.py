#!/usr/bin/env python3
"""Render docs/tool-map.html - a single self-contained page listing every tool.

Same two inputs as TOOLS.md: the server's own tools/list reply and the recorded
response shapes. No network, no CDN, no build step; open the file.

    python3 tools/gen_tool_map_html.py
"""

import html
import json
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_tools_md import ENDPOINT, PROMPT, load_tools, cost_of, first_sentence  # noqa: E402

CSS = """
:root {
  --bg: #fbfbfa; --fg: #1a1a18; --muted: #6b6b64; --line: #dedad2;
  --panel: #ffffff; --accent: #7a4a12; --code: #f3f1ec;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #14140f; --fg: #e8e6df; --muted: #9a978c; --line: #33322b;
    --panel: #1b1b16; --accent: #d9a05b; --code: #22221b;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 15px/1.55 ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif;
}
.wrap { max-width: 1040px; margin: 0 auto; padding: 40px 20px 80px; }
h1 { font-size: 23px; font-weight: 600; margin: 0 0 6px; letter-spacing: -0.01em; }
.sub { color: var(--muted); font-size: 14px; margin: 0 0 4px; }
.meta { color: var(--muted); font-size: 13px; margin: 18px 0 0;
        border-top: 1px solid var(--line); padding-top: 14px; }
code, .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
              font-size: 12.5px; }
.controls { margin: 26px 0 14px; display: flex; gap: 10px; flex-wrap: wrap;
            align-items: center; }
input[type=search] {
  flex: 1 1 260px; padding: 8px 11px; border: 1px solid var(--line);
  border-radius: 5px; background: var(--panel); color: var(--fg); font-size: 14px;
}
.count { color: var(--muted); font-size: 13px; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; }
thead th {
  text-align: left; font-size: 11.5px; letter-spacing: 0.07em; text-transform: uppercase;
  color: var(--muted); font-weight: 600; padding: 8px 10px; border-bottom: 1px solid var(--line);
}
tbody td { padding: 11px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
tbody tr.t:hover { background: var(--panel); }
td.name { word-break: break-word; }
td.name b { font-family: ui-monospace, Menlo, monospace; font-weight: 600; font-size: 13px; }
td.cost { white-space: nowrap; color: var(--muted); font-size: 13px; }
td.ep { color: var(--muted); word-break: break-all; }
.free { color: var(--accent); }
.det { display: none; }
.det.open { display: table-row; }
.det td { background: var(--panel); padding: 4px 10px 18px; }
.det .inner { max-width: 100%; }
.det h3 { font-size: 12px; letter-spacing: 0.06em; text-transform: uppercase;
          color: var(--muted); margin: 16px 0 6px; font-weight: 600; }
.det p { margin: 0; }
blockquote { margin: 0; padding: 9px 13px; border-left: 2px solid var(--accent);
             background: var(--code); border-radius: 0 4px 4px 0; }
pre { background: var(--code); padding: 10px 12px; border-radius: 4px;
      overflow-x: auto; margin: 0; white-space: pre; }
blockquote, .det p { overflow-wrap: anywhere; }
.toggle { cursor: pointer; background: none; border: none; color: var(--accent);
          font: inherit; font-size: 12.5px; padding: 0; }
.err { color: #b3261e; }
@media (prefers-color-scheme: dark) { .err { color: #ef9a93; } }
.foot { margin-top: 46px; padding-top: 16px; border-top: 1px solid var(--line);
        color: var(--muted); font-size: 12.5px; }
.foot a { color: var(--accent); }
"""

JS = """
const q = document.getElementById('q');
const rows = [...document.querySelectorAll('tr.t')];
const count = document.getElementById('count');
function filter() {
  const v = q.value.trim().toLowerCase();
  let n = 0;
  for (const r of rows) {
    const hit = !v || r.dataset.hay.includes(v);
    r.hidden = !hit;
    const d = r.nextElementSibling;
    if (d && d.classList.contains('det')) { d.hidden = !hit; }
    if (hit) n++;
  }
  count.textContent = n + ' of ' + rows.length + ' tools';
}
q.addEventListener('input', filter);
document.querySelectorAll('.toggle').forEach(b => {
  b.addEventListener('click', () => {
    const d = document.getElementById(b.dataset.for);
    const open = d.classList.toggle('open');
    b.textContent = open ? 'hide' : 'details';
  });
});
filter();
"""


def shape_html(entry):
    if not entry:
        return "<p class='mono'>not called</p>"
    if not entry.get("ok"):
        return ("<p class='mono err'>the call failed when we ran it: %s</p>"
                % html.escape(str(entry.get("error"))))
    sh = entry.get("shape", {})
    lines = ["top level: {%s}" % ", ".join('"%s"' % k for k in sh.get("keys", []))]
    data = sh.get("data")
    if isinstance(data, dict):
        if data.get("type") == "array":
            lines.append("data: array (%d rows when called)" % data.get("length", 0))
            if data.get("first_item_keys"):
                lines.append("row keys: " + ", ".join(data["first_item_keys"]))
        elif data.get("type") == "object":
            lines.append("data: object")
            lines.append("keys: " + ", ".join(data.get("keys", [])))
    return "<pre>%s</pre>" % html.escape("\n".join(lines))


def main():
    tools = load_tools()
    shapes = json.load(open(os.path.join(ROOT, "docs", "tool-shapes.json")))
    st = shapes["tools"]

    body = []
    for i, t in enumerate(tools):
        name = t["name"]
        cost = cost_of(t.get("description"))
        ep = ENDPOINT.get(name, "?")
        entry = st.get(name)
        params = list((t.get("inputSchema") or {}).get("properties", {}).keys())
        req = (t.get("inputSchema") or {}).get("required", [])
        hay = " ".join([name, cost, ep, " ".join(params),
                        (t.get("description") or "")]).lower()
        cost_cls = " free" if cost.strip().lower().startswith("free") else ""
        body.append(
            "<tr class='t' data-hay=\"%s\">"
            "<td class='name'><b>%s</b></td>"
            "<td class='cost%s'>%s</td>"
            "<td class='ep mono'>%s</td>"
            "<td><button class='toggle' data-for='d%d'>details</button></td></tr>"
            % (html.escape(hay, quote=True), html.escape(name), cost_cls,
               html.escape(cost), html.escape(ep), i))
        body.append(
            "<tr class='det' id='d%d'><td colspan='4'><div class='inner'>"
            "<h3>What it is</h3><p>%s</p>"
            "<h3>Parameters</h3><p class='mono'>%s</p>"
            "<h3>Ask an assistant</h3><blockquote>%s</blockquote>"
            "<h3>What came back (%s, arguments <code>%s</code>)</h3>%s"
            "</div></td></tr>"
            % (i, html.escape(first_sentence(t.get("description"))),
               html.escape(", ".join("%s%s" % (p, " (required)" if p in req else "")
                                     for p in params) or "none"),
               html.escape(PROMPT.get(name, "-")),
               html.escape(shapes["captured_at"]),
               html.escape(json.dumps((entry or {}).get("arguments", {}))),
               shape_html(entry)))

    page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PuntersEdge MCP tool map</title>
<style>%s</style></head><body><div class="wrap">
<h1>PuntersEdge MCP server &mdash; tool map</h1>
<p class="sub">Australian and New Zealand racing, Australian sports. Every tool the
server exposes, its credit cost, the HTTP endpoint behind it, and the keys that
actually came back when each one was called.</p>
<p class="meta">Generated from the server's own <code>tools/list</code> reply and from
<code>docs/tool-shapes.json</code>, which records one real call per tool.
Server <code>%s</code> &middot; %d tools &middot; swept %s.
Costs are the server's own figures. A malformed request is refused without being billed.</p>
<div class="controls">
  <input type="search" id="q" placeholder="filter by name, cost, endpoint or parameter">
  <span class="count" id="count"></span>
</div>
<table>
<colgroup><col style="width:29%%"><col style="width:17%%"><col style="width:43%%"><col style="width:11%%"></colgroup>
<thead><tr><th>Tool</th><th>Cost</th><th>HTTP endpoint</th><th></th></tr></thead>
<tbody>%s</tbody></table>
<p class="foot">Regenerate: <code>python3 tools/gen_tool_map_html.py</code>.
Free API key, 1,500 credits a month, no card:
<a href="https://puntersedge.online/api?utm_source=puntersedge-mcp-examples&amp;utm_medium=docs">puntersedge.online/api</a>
&middot; <a href="https://puntersedge.online/coverage-report?utm_source=puntersedge-mcp-examples&amp;utm_medium=docs">coverage report</a><br><br>
18+ only. Gambling can be addictive &mdash; please gamble responsibly.
Gambling Help: 1800 858 858 &middot;
<a href="https://www.gambleaware.nsw.gov.au">gambleaware.nsw.gov.au</a><br>
A developer reference for reading an odds data feed. Not betting advice; places no bets.</p>
</div><script>%s</script></body></html>
""" % (CSS, html.escape(shapes["server_command"]), shapes["tool_count"],
       html.escape(shapes["captured_at"]), "\n".join(body), JS)

    out = os.path.join(ROOT, "docs", "tool-map.html")
    open(out, "w").write(page)
    print("wrote %s (%d bytes)" % (out, len(page)))


if __name__ == "__main__":
    main()
