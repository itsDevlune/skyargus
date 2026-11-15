# Image-centered explorer verification - 2026-11-15

Implemented in the existing Django/Canvas application. Existing SQLite data, artifact files and immutable report snapshots were retained. No schema migration or replacement imagery was introduced.

## Geometry investigation

The controls send **full width and height in arcminutes**. `region()` validates and normalizes them. SIA discovery uses a cone radius `hypot(width,height)/120` degrees, sufficient to enclose the requested rectangle. The IBE archive download asks for an oversized square `hypot(width,height)*1.15` arcminutes, capped at 30, to accommodate detector rotation. This archive footprint is distinct from the displayed requested rectangle.

`grid()` divides each requested angular dimension by the 6.2 arcsec display-grid scale and rounds the pixel count. Its TAN WCS is north up/east left. `read_frame()` reprojects the actual FITS IMAGE HDU to that grid, leaves nonfinite/no-coverage pixels blank, and records native returned footprint separately from finite-data coverage. Raw quality flags remain separate; finite coverage does not establish photometric validity.

A 6 arcmin request produces 58x58 pixels and about 5.9933 arcmin width. A 12 arcmin request produces 116x116 pixels and about 11.9867 arcmin width. Actual spherical separations are measured between WCS pixel-edge midpoints; rounding error is below one pixel. Regression checks use the real archived SPHEREx FITS fixture, its actual celestial WCS, and a rectangular 12x6 arcmin case. A deliberately inconsistent cached 12 arcmin request/58-pixel WCS is detected.

The initial audit of existing SPHEREx cache records found 6x6 arcmin requests and 58x58 grids, not a persisted 12 arcmin/58-pixel SPHEREx result. The existing 12 arcmin cache was NEOSSat native detector data, for which sky FOV is discovery-only. The screenshot alone cannot prove a backend mismatch. Editing FOV previously left old imagery silently visible. The UI now labels pending request edits, the loaded request and the WCS-derived output separately, and refuses preview dimensions inconsistent with recorded grid dimensions. Old records lacking returned-native-footprint metadata say so rather than inventing it. See `evidence/explorer-redesign/geometry-audit.json`.

## Epochs and wavelength

New SPHEREx processing uses `argus-0.2-grid-v3-geometry-epochs`. Within the bounded 100-row returned metadata sample, up to eight observations include the earliest/latest and maximize temporal spread, instead of taking only the first eight. Existing reports/sequences remain pinned. Discovery reports sampled and selected time ranges and possible truncation. The timeline displays the **actual loaded-frame baseline**, which can be shorter when endpoint downloads fail.

Live new-processing data observed locally: sequence `360f728f-b81d-409e-b310-70200f4b82cd` has seven usable frames spanning 2025-05-21 to 2025-12-02 (194.9363 days). Sequence `93924ac9-a107-4bb6-8f92-e0aee7b106a3` selected endpoints spanning 196.5578 days but usable frames span only 8.8947 days after download exclusions; the displayed baseline follows usable frames. These are bounded samples, not archive completeness claims.

Single mode explicitly shows one dated exposure, **not combined**. Comparisons show field-center wavelength-band overlap, and warn when bands are disjoint. Same detector, WCS alignment or overlap alone does not establish calibrated response/PSF/photometric comparability. No upsampling is claimed to recover scientific resolution.

## Workspace and manual checks

Search toolbar holds source, name and requested FOV. Coordinates, release, detector, dates, presets and limits expand under Request details. Load resolves a new object name before submission; explicit coordinates remain supported. A pending request never relabels the previous image.

Fit Image fits the loaded grid; Native Pixels maps one loaded display-grid pixel to one CSS pixel (not an unreprojected detector pixel). Zoom/pan/reset work on the same viewport. Playback, stepping, timeline dates and comparison controls stay beside the image. Evidence is collapsed initially; Mark opens source evidence. Observations holds the log. Analysis retains selection and viewport. Manual motion remains implemented; calibrated spectra, subtraction and stacking are explicitly unavailable pending their scientific backends.

To test: open a cached field, edit FOV and check pending versus loaded geometry; Load and inspect WCS size after completion. Click Fit Image, Native Pixels, zoom, drag and Reset. Step dates, Play/Pause, move timeline and compare frames. Mark a source, switch panels and verify coordinates/viewport persist. Save an annotation, then an immutable report; inspect its selected-frame PNG. On a partial sequence, expand failures and retry: old evidence remains pinned. Names may need the live external resolver; outages remain visible without replacing images.

## Executed checks and evidence

- Python: **58 passed**; includes real FITS/WCS geometry, coverage, cache mismatch, temporal-spread selection, wavelength diagnostic, ownership, malformed UUID and selected-frame export regressions.
- Playwright: **11 passed, no skips locally**. Viewport layout at 1366x768, 1920x1080 and 390x844; fit/native sizing; pending FOV; panel selection retention; annotation/report saving; comparison aspect ratio; copied pan/contrast state; partial retry request. Real cached backend search, automatic object-resolution submission, Play/Pause, previous/next, drag pan, reset and controlled 12 arcmin outage preservation also passed at 1366x768. A load/step race found during testing was fixed by enabling frame controls only once initial loading completes.
- Name resolution and retry/outage fault branches use controlled responses while rendering genuine cached archive images; they do not establish live upstream success. The bounded live 12 arcmin request failed on both bounded attempts with `archive_connection_failed`; its failure evidence is retained. No fake successful live measurement is claimed.
- Ruff, frontend build and whitespace checks executed. Linux/Postgres/Celery/deployment not tested.

Before/after screenshots are under `evidence/explorer-redesign/before/` and `after/` for all three widths. The 1366 baseline had playback below the viewport (y791); the redesign puts it at y679.5, with a 386px image stage. At 1920 the image stage is 698px high; at mobile 352px. All three have visible playback, hidden default inspector, no horizontal overflow and no captured JavaScript errors. Exact boxes: `after/layout.json`. Screenshots use real cached data, not a mockup.
