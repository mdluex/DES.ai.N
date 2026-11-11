# Troubleshooting

## Local model not found

- Confirm LM Studio / Ollama / llama.cpp is running with an OpenAI-compatible server.
- Check `DESAIN_LLM_BASE_URL` (default `http://127.0.0.1:1234/v1`).
- Set `DESAIN_LLM_AUTO_DETECT=true` and watch the system log for detected endpoints.
- The agent falls back to JSON action plans if native tool-calling fails.

## Malformed tool / JSON actions

Small models often wrap JSON in markdown fences or emit trailing commas. The
local runtime repairs and retries once. If actions are still skipped, switch to a
stronger instruct model or lower temperature in the server UI.

## Photoshop bridge not connected

**UXP:** start the app (or `desain-mcp`), load `uxp-plugin/`, open the bridge panel, click Connect.

**COM (Windows):** ensure Photoshop is installed and COM-registered; install `pywin32` in the venv.

**Mock:** set `DESAIN_BRIDGE_BACKEND=mock` for UI/agent dry-runs without Photoshop.

## Unsplash failures

Set `UNSPLASH_ACCESS_KEY` in `.env`, or pass a local image `path` to image tools.

## Timeouts

Raise `DESAIN_BRIDGE_TIMEOUT_S` for Generative Fill and large documents.

## Limitations

See [limitations.md](limitations.md).
