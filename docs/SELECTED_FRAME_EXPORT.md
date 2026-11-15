# Selected-frame PNG and regression verification — 2026-11-15

All four requested items are now covered:

1. Side-by-side uses one scale factor for both image axes, preserving each image's native aspect ratio. The browser test measures draw dimensions against the source image rather than assuming a square DOM container is sufficient.
2. Copied view links contain panX, panY and contrast. A browser regression copies the actual URL, reopens it and checks restored offsets/contrast, frame and B selection.
3. PNG export reads the selected index from the immutable report's settings.index, draws that observation and only its frame-matching annotations. PNG metadata includes report ID, zero-based frame index, observation ID, observation time and real/simulated mode. Annotation coordinates use the actual rendered image dimensions. GIF still exports the whole ordered sequence.
4. API request validation catches malformed UUID ValidationError and responds with JSON invalid_request/400 on candidate/report POSTs. Existing regression tests remain passing.

To export a different observation: select it in Explorer, save the report (or a new revision), then open that revision and choose Annotated PNG. Export is pinned to the selected frame saved with that revision; moving the live viewer later does not silently change an immutable report. Older reports with no saved selection retain first-frame fallback. An invalid saved selection returns 422 instead of exporting the wrong observation.

Verification: **51 Python tests passed**, including nine export regressions (selected nonzero frame, correct annotation placement/no annotation leakage, GIF order, invalid indices, old-report fallback, private ownership). **Five Playwright tests passed**, including copied view-link roundtrip and aspect-ratio checks against the installed real cached sequence. Ruff passed. Tests are offline; no archive requery was needed.
