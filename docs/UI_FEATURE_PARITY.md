# Explorer parity audit — in progress

The running Django templates and ES modules are the source of truth. This audit and redesign are not complete.

| Existing capability | Current implementation | Destination |
| --- | --- | --- |
| Explorer, investigations, sources, help, theme | base.html / common.js | Compact global header |
| Source, resolver, FOV, load, cancellation | explorer.html / explorer.js search-form | Search toolbar |
| Units, RA/Dec, release, detector, dates, presets | request-details | Request settings |
| Pending request versus loaded field | updateRequestState | Search status |
| Pan, mark, fit, native pixels, reset, target, HiPS, fullscreen | viewer-tools / explorer.js | Viewer toolbar |
| Exposure, blink, side-by-side, swipe, mosaic | mode / draw | Viewer mode selector |
| Playback, speed, loop, dates, frame count | timeline / frame | Timeline below image |
| Interpolation, stretch, HiPS layer, contrast, compare B, swipe, URL | lower-tools | Display and wavelength controls |
| Observation rows, downloads, partial failures, retry | renderRows | Observations workbench |
| Evidence, warnings, provenance, native and aligned FITS | evidence-panel | Inspector |
| Candidate selection, classification, notes, clear/save | annotation / refreshMarks | Inspector |
| Gaia reference context and overlay | gaia / explorer.js | Inspector |
| Report save, reopen, JSON export, sharing, revoke | common.js / report templates | Investigations |
| Motion, spectra, difference, stacking, composite | analysis.js / analysis-content | Analysis workbench |

Every ID and handler is retained in this initial visual pass. Full interaction and rendered-state verification remains outstanding, including graphs, exports, ownership, keyboard, mobile and cached observation screenshots.

## Token reference

Background #090E20; elevated surface #1A2340; action #B9A5FF; selection #65E2DD; text #F1F3FF; secondary #ABB5CF. Existing light theme remains available. Shared styles reside in app.css (base components) and workspace.css (workspace layout). No remote font was added.

## Evidence

Initial shell capture: ui-before.png. This is an empty workspace capture, not evidence of a live archive retrieval. The initial palette/layout pass is not the requested finished redesign.

## Continued implementation

Analysis and Observations now use the expandable lower workbench; Evidence retains its right inspector. Panel changes retain the existing state object. Dismissing a panel returns focus to its opener when focus was inside it. Mobile exposes contrast reset and swipe controls that were previously hidden. Display controls wrap and mobile permits vertical scrolling.

Cached observation screenshots: ui-after-1920.png, ui-after-1366.png, ui-after-1024.png, ui-after-768.png, ui-after-390.png. All five captures used installed real sequence 3122bdf8-1727-44ff-ad8c-aac23cffe151, not a new live retrieval. No horizontal overflow was measured. Playback stayed within the viewport on all desktop/tablet sizes; mobile uses vertical scrolling. The 1366 screenshot was visually inspected.

Two viewer regressions passed. The workspace interaction test fails its expectation that a single zoom step always permits 40 pixels of horizontal pan; current image-boundary constraints clamp that movement. This remains unresolved and is not recorded as a passing interaction test. Full parity, all-size visual inspection, graph verification and accessibility checks remain incomplete.
