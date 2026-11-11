# Limitations

- **No live Photoshop verification in CI.** Automated tests use the mock bridge
  and a WebSocket hub fake client. UXP DOM/batchPlay behaviour must be validated
  on a machine with Photoshop installed.
- **Adobe official Creative Cloud MCP** (announced at MAX 2026) is preview /
  early-2027 private beta. DES.ai.N does not depend on it yet; when Adobe ships
  a stable local MCP endpoint, a thin adapter backend can be added beside UXP/COM.
- **UXP API surface varies by Photoshop version.** Some operations (Generative
  Fill action IDs, Select Subject descriptors, text style setters) differ across
  builds. Errors are returned as structured JSON rather than crashing the server.
- **macOS COM is unavailable.** Use the UXP bridge on macOS.
- **Vision QA / reference recreation** remain part of the optional PyQt agent
  loop (`core/ai_agent.py`), not the MCP tool surface.
- **Arabic / RTL typography** and embedding-based template matching are still
  unfinished (see roadmap in README).
- **License:** Source-available, non-commercial by default — see `LICENSE`.
