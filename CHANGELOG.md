# Changelog
## 0.1 development — 2026-11-15
- Created Django explorer, durable jobs/storage, session-owned candidate notes and immutable reports/shares.
- Integrated actual SPHEREx DR1/QR3 discovery, native FITS cutouts, display WCS reprojection and shared-stretch previews.
- Added Gaia DR3 query/overlay and separate CADC NEOSSat native raw detector workflow.
- Added motion numerical kernel/job, report PNG/GIF/print/FITS access, build/deployment files and evidence ledger.
- Corrected alternate WCS wavelength raw-detector offsets in processing v2; old unvalidated report snapshots remain unchanged.
- 29 offline Python and 3 browser shell tests passed. Full release and Linux/deployment gates remain open.

### Workspace corrections
- Enlarged and balanced the scientific workspace, readable controls and desktop evidence inspector.
- Compact partial-results summary and retry action preserve saved evidence.
- Fixed comparison distortion, view-state mismatch, native cursor and audit validation defects.
- 42 Python tests and 5 Playwright tests pass; API audit 12/12 passes.

Selected-frame export update: PNG now uses the immutable report settings.index and only that frame's annotations, with identity/time PNG metadata; GIF retains all frames. 51 pytest tests and 5 Playwright tests passed. Copied pan/contrast URL roundtrip, side-by-side proportions and malformed-UUID 400 handling verified. See docs/SELECTED_FRAME_EXPORT.md (SELECTED_FRAME_EXPORT.md from within docs).

## Image-centered scientific workspace
Compact search with expandable request details; dominant viewer with Fit/Native pixels, visible playback and overlay Evidence/Observations/Analysis panels. Added actual-WCS footprint diagnostics, pending request warning, loaded baseline and visualization band-overlap caution. New bounded metadata selection spreads observations across time. Existing data/report snapshots retained. See docs/EXPLORER_REDESIGN.md for executed checks and upstream limitations.
