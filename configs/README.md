# Config blocks, and where each one goes

Every file here is a complete, valid config. Copy it, replace
`PUT-YOUR-KEY-HERE` with a key from
[puntersedge.online/api](https://puntersedge.online/api?utm_source=puntersedge-mcp-examples&utm_medium=docs),
and restart the client.

Two servers exist. `puntersedge-mcp` is the Python one from PyPI (26 tools);
`npx -y github:Propertyscout001/puntersedge-mcp` is the TypeScript one from
GitHub (9 tools). There is **no npm package called `puntersedge-mcp`** —
`npm install -g puntersedge-mcp` will always fail with a 404. See the root
README for the comparison.

| File | Client | Where it goes |
|---|---|---|
| `claude-desktop.json` | Claude Desktop | macOS: `~/Library/Application Support/Claude/claude_desktop_config.json` · Windows: `%APPDATA%\Claude\claude_desktop_config.json`. Reachable from the app: Settings → Developer → Edit Config. |
| `claude-desktop-typescript.json` | Claude Desktop | Same file. Use this one if you would rather not install a Python package — `npx` fetches the TypeScript server. |
| `claude-code.mcp.json` | Claude Code | `.mcp.json` in the project root, for a server you want committed and shared with the repo. |
| `cursor.mcp.json` | Cursor | `.cursor/mcp.json` in the project, or `~/.cursor/mcp.json` for every project. |
| `generic-stdio-client.json` | anything else that launches a stdio MCP server | Wherever that client keeps its server list. `PUNTERSEDGE_BASE_URL` is optional and only needed to point at something other than production. |

## Claude Code without editing a file

```
claude mcp add puntersedge -e PUNTERSEDGE_API_KEY=your-key-here -- puntersedge-mcp
```

That is the form the PuntersEdge docs give, and it uses the CLI's default
`local` scope — private to you, for this project, no approval step.

`--scope project` writes `.mcp.json` into the repo instead, which is the file in
this directory. Worth knowing before you choose it: a project-scope server is
**pending approval** until someone runs `claude` interactively and approves it.
Running `claude mcp list` straight after adding one prints:

```
puntersedge: puntersedge-mcp  - ⏸ Pending approval (run `claude` to approve)
```

That is the checked-in-config safety prompt doing its job, not a broken install.

## Keeping the key out of the file

Every one of these clients passes `env` straight through to the server process,
and the server reads `PUNTERSEDGE_API_KEY` once at start-up. If you would rather
not have the key sitting in a JSON file at all, drop the `env` block and export
the variable in the shell that launches the client — the server picks it up from
the inherited environment either way.

Do not commit a filled-in copy. `.gitignore` in this repo already ignores
`configs/*.local.json`, so `cp cursor.mcp.json cursor.local.json` gives you a
scratch copy that cannot be committed by accident.
