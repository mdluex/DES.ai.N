# Limitations

- Automated CI uses the mock Photoshop bridge. Validate UXP/COM behaviour on a
  machine with Photoshop installed before relying on a new release for production work.
- Local model quality varies widely. Tiny models may need JSON-action mode and
  more turns; vision QA requires a vision-capable model.
- UXP DOM / batchPlay details differ across Photoshop versions. Failures return
  structured errors instead of crashing the app.
- Windows COM is unavailable on macOS — use the UXP bridge there.
- Arabic / RTL typography and embedding-based template matching are unfinished.
- License is source-available and non-commercial by default — see `LICENSE`.
