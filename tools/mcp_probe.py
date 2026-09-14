#!/usr/bin/env python3
"""mcp_probe.py - a dependency-free MCP stdio client.

Speaks newline-delimited JSON-RPC 2.0 to an MCP server on stdin/stdout, which is
what Claude Desktop, Claude Code and Cursor do when they launch a stdio server.
Use it to check that a server actually starts, to list its tools, and to call one
of them - without an assistant in the loop.

Examples
--------
  # handshake + tool list, no API key needed
  python3 tools/mcp_probe.py --list -- puntersedge-mcp

  # call the keyless demo tool
  python3 tools/mcp_probe.py --call demo_next_to_go -- puntersedge-mcp

  # call a keyed tool (server reads PUNTERSEDGE_API_KEY from the environment)
  python3 tools/mcp_probe.py --call racing_next_to_go \
      --args '{"country":"AU","num_races":3}' -- puntersedge-mcp

  # the TypeScript server, fetched straight from GitHub
  python3 tools/mcp_probe.py --list -- npx -y github:Propertyscout001/puntersedge-mcp

Everything it prints is the raw protocol: the exact JSON-RPC frames sent and
received. Nothing is reformatted for readability beyond indentation.
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time

PROTOCOL_VERSION = "2025-06-18"


class StdioClient:
    def __init__(self, argv, env=None, verbose=True, timeout=60.0, truncate=0):
        self.argv = argv
        self.verbose = verbose
        self.timeout = timeout
        self.truncate = truncate
        self._id = 0
        self.stderr_lines = []
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env or os.environ.copy(),
            text=True,
            bufsize=1,
        )
        t = threading.Thread(target=self._drain_stderr, daemon=True)
        t.start()

    def _drain_stderr(self):
        for line in self.proc.stderr:
            self.stderr_lines.append(line.rstrip("\n"))

    def _shorten(self, payload):
        """Clip oversized tool-result bodies so a transcript stays readable.

        Only the payload *inside* a frame is clipped, and the clip is marked
        in place. The JSON-RPC framing itself is never altered.
        """
        if not self.truncate:
            return payload
        n = self.truncate

        def clip(text):
            if not isinstance(text, str) or len(text) <= n:
                return text
            return (text[:n] +
                    "  <<< clipped by mcp_probe --truncate %d; full body was %d chars >>>"
                    % (n, len(text)))

        payload = json.loads(json.dumps(payload))
        result = payload.get("result")
        if isinstance(result, dict):
            for item in result.get("content", []) or []:
                if isinstance(item, dict) and "text" in item:
                    item["text"] = clip(item["text"])
            sc = result.get("structuredContent")
            if isinstance(sc, dict):
                for k, v in list(sc.items()):
                    sc[k] = clip(v) if isinstance(v, str) else v
        return payload

    def _emit(self, direction, payload):
        if not self.verbose:
            return
        arrow = "-->" if direction == "send" else "<--"
        shown = payload if direction == "send" else self._shorten(payload)
        print("%s %s" % (arrow, json.dumps(shown, indent=2, sort_keys=False)))
        print()

    def send(self, payload):
        self._emit("send", payload)
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def read_message(self):
        """Read one JSON-RPC frame. Skips any non-JSON line a server may print."""
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            line = self.proc.stdout.readline()
            if line == "":
                raise RuntimeError(
                    "server closed stdout before replying. stderr:\n"
                    + "\n".join(self.stderr_lines[-20:])
                )
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                # Not protocol traffic - a server logging to stdout. Note and move on.
                if self.verbose:
                    print("(non-JSON line on stdout, ignored) %s" % line[:200])
                continue
            self._emit("recv", msg)
            return msg
        raise TimeoutError("no JSON-RPC frame within %.0fs" % self.timeout)

    def request(self, method, params=None):
        self._id += 1
        payload = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            payload["params"] = params
        self.send(payload)
        while True:
            msg = self.read_message()
            # Ignore notifications and any server->client request while we wait.
            if msg.get("id") == self._id:
                return msg

    def notify(self, method, params=None):
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self.send(payload)

    def initialize(self, client_name="mcp_probe", client_version="1.0.0"):
        resp = self.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": client_name, "version": client_version},
            },
        )
        self.notify("notifications/initialized")
        return resp

    def close(self):
        try:
            self.proc.stdin.close()
        except Exception:
            pass
        try:
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def extract_payload(resp):
    """Pull the tool body out of a tools/call response.

    The PuntersEdge servers put their JSON body in content[0].text as a
    *string*, so a client has to json.loads it a second time. If that ever
    stops being true this falls back to returning the raw result.
    """
    result = resp.get("result")
    if not isinstance(result, dict):
        return resp
    for item in result.get("content", []) or []:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            try:
                return json.loads(item["text"])
            except json.JSONDecodeError:
                return item["text"]
    return result


def main():
    p = argparse.ArgumentParser(
        description="Dependency-free MCP stdio client for verifying a server.",
        epilog="Put the server command after a bare --, e.g. ... -- puntersedge-mcp",
    )
    p.add_argument("--list", action="store_true", help="call tools/list")
    p.add_argument("--call", metavar="TOOL", help="call one tool by name")
    p.add_argument("--args", metavar="JSON", default="{}",
                   help="JSON object of tool arguments (default: {})")
    p.add_argument("--timeout", type=float, default=90.0,
                   help="seconds to wait for each frame (default: 90)")
    p.add_argument("--truncate", type=int, default=0, metavar="N",
                   help="clip tool-result bodies to N characters in the printed "
                        "transcript (0 = print everything). Framing is never clipped.")
    p.add_argument("--extract", action="store_true",
                   help="with --call, print only the decoded tool payload as JSON. "
                        "The server returns its body as a JSON *string* inside "
                        "content[0].text, so this does the json.loads for you.")
    p.add_argument("--names-only", action="store_true",
                   help="with --list, print just the tool names and costs")
    p.add_argument("server", nargs=argparse.REMAINDER,
                   help="the server command, after --")
    a = p.parse_args()

    argv = [x for x in a.server if x != "--"]
    if not argv:
        p.error("no server command given. Put it after a bare --")

    verbose = not (a.names_only or a.extract)
    if not a.extract:
        print("# mcp_probe %s" % time.strftime("%Y-%m-%dT%H:%M:%S%z"))
        print("# server: %s" % " ".join(argv))
        print("# protocolVersion offered: %s" % PROTOCOL_VERSION)
        print("# key present in env: %s"
              % ("yes" if os.environ.get("PUNTERSEDGE_API_KEY") else "no"))
        print()

    c = StdioClient(argv, verbose=verbose, timeout=a.timeout,
                    truncate=a.truncate)
    rc = 0
    try:
        init = c.initialize()
        if a.names_only:
            info = init.get("result", {}).get("serverInfo", {})
            print("initialize ok: %s %s (protocol %s)" % (
                info.get("name"), info.get("version"),
                init.get("result", {}).get("protocolVersion")))
        if a.list:
            resp = c.request("tools/list")
            tools = resp.get("result", {}).get("tools", [])
            if a.names_only:
                print("\n%d tools:" % len(tools))
                for t in tools:
                    desc = (t.get("description") or "").strip().replace("\n", " ")
                    print("  %-28s %s" % (t["name"], desc[:96]))
            else:
                print("# tools/list returned %d tools" % len(tools))
        if a.call:
            resp = c.request("tools/call",
                             {"name": a.call, "arguments": json.loads(a.args)})
            if a.extract:
                print(json.dumps(extract_payload(resp), indent=2))
            elif a.names_only:
                print(json.dumps(resp.get("result", resp), indent=2)[:4000])
    except Exception as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        rc = 1
    finally:
        if c.stderr_lines and not a.extract:
            print("# --- server stderr ---")
            for line in c.stderr_lines[-40:]:
                print("# %s" % line)
        c.close()
    sys.exit(rc)


if __name__ == "__main__":
    main()
