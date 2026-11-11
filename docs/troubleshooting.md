# Troubleshooting

## `BRIDGE_NOT_CONNECTED`

The MCP server is running but no UXP plugin (or COM session) is attached.

1. Confirm `desain-mcp` is running.
2. In Photoshop, open **Plugins → DES.ai.N Bridge** and click **Connect**.
3. Verify the URL matches `DESAIN_BRIDGE_HOST` / `DESAIN_BRIDGE_PORT`.
4. Check that UXP Developer Tool loaded `uxp-plugin/manifest.json` without errors.

## `BRIDGE_TIMEOUT`

Photoshop took longer than `DESAIN_BRIDGE_TIMEOUT_S` (default 60s). Generative
Fill and large document opens are the usual causes — raise the timeout or retry.

## Unsplash failures

Set `UNSPLASH_ACCESS_KEY` in `.env`. Tools also accept a local `path` to skip
Unsplash entirely.

## COM backend on Windows

- Photoshop must be installed and COM-registered.
- Install `pywin32` inside the venv.
- Set `DESAIN_BRIDGE_BACKEND=com`.

## MCP client cannot start the server

Use an absolute path to the venv executable. Relative paths and shell aliases
often fail inside GUI MCP hosts.

## Unit tests without Photoshop

```bash
DESAIN_BRIDGE_BACKEND=mock pytest -q
```

## Limitations

See [limitations.md](limitations.md).
