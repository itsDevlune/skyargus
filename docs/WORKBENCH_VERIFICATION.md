# Frontend verification — 2026-11-15

Latest workspace rewrite: replaced workspace.css rather than adding another override layer. Search is prioritized ahead of mission selection through the responsive grid. Detailed request settings retain their existing form controls. Display and wavelength settings now have a semantic collapsible section in explorer.html. Existing IDs and event handlers are retained. All 30 browser checks and the real cached report/share/export round-trip passed after this rewrite. Refreshed all five viewport captures; no horizontal overflow. Backend files were not changed.

The frontend keeps the existing API requests, scientific values, persisted data and report permissions. No backend files were edited in this redesign continuation.

## Drag investigation

Pointer capture and DOM coordinates were functioning. At Fit and small zoom levels a square image is narrower than the desktop viewport. The existing boundary constraint correctly clamps horizontal displacement. Two tests incorrectly expected unrestricted movement at that scale. They now zoom beyond both viewport axes before making the same movement assertions; neither test was removed or skipped. Primary-button handling and lost-pointer-capture cleanup were added. Pan and Mark retain distinct handlers and celestial marking restrictions.

## Results

- All 30 Playwright tests passed, including real cached drag, selection, playback, comparison, pending requests, URL restoration, analysis selectors, partial failures and provenance checks.
- 217 Python tests passed, with three existing Astropy boundary warnings.
- Repository-wide Ruff reports three findings in docs/evidence/workbench/aperture_photometry.py (import order and two unused variables). This scientific evidence file was left unchanged under the frontend-only boundary.
- Refreshed and visually inspected cached observation captures at 1920x1080, 1366x768, 1024x768, 768x1024 and 390x844. Desktop playback is visible. Mobile advanced controls use vertical scrolling. No horizontal overflow in these captures.
- These observations came from the local real archive cache; this is not evidence of a fresh archive retrieval.

## Scope limits

## Saved-data round trip

`node scripts/ui-roundtrip.cjs` created private verification annotations and immutable reports from genuine cached observations. Evidence is in `docs/evidence/ui-roundtrip/`. Results verify frame 2, contrast 1.5, saved selected coordinates and annotation text after reopening, a read-only share in a fresh context, and HTTP 404 after revocation. A frontend bug in report continuation was fixed: it now reads existing saved settings and restores the selected point, display settings and title.

All five analysis jobs completed on cached data (spectrum, difference, stack, composite, motion); exact requests and results are saved in analysis-results.json. These job outcomes do not imply independent validation of the underlying scientific algorithms. Spectrum returned six measured points with uncertainties; stack recorded two contributors; difference retained comparability warnings; RGB recorded all three channel identities.

PNG metadata was inspected for FrameIndex=1 and the corresponding observation ID. GIF contains eight frames matching the report sequence. JSON contains saved manual annotations. PDF has a valid PDF header; this does not establish print accessibility. Separate screenshots preserve open Analysis, Evidence and report pages. The reusable script does not delete prior user data; its own verification annotations/reports remain in their private sessions.

Ruff findings retained unchanged: docs/evidence/workbench/aperture_photometry.py — I001 import ordering; F841 flux_out_unit; F841 var_out_unit.

The browser suite exercises report and graph presentation only to the extent covered by existing tests. It does not establish an exhaustive manual round-trip test of every saved report, sharing permission or analysis result. Existing light mode is retained. Real device touch/pinch and screen-reader testing were not performed.
