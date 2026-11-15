# Argus: complete browser user-test checklist

Use this against the current implementation. This is a test procedure, not a statement that every requested feature is complete. Feature status remains in FEATURES.md; scientific and live-service limits are in WORKBENCH_VERIFICATION.md.

## Preparation and scoring

1. Open Chrome or Edge at http://127.0.0.1:8000/. The web server and background worker must already be running. A page that cannot connect means the server is stopped; a job that remains queued can mean the worker is stopped.
2. Use a separate browser profile for QA, keeping its cookies between tests. Name notes/reports `QA TEST - date - case`. Do not clear existing annotations, cookies or reports belonging to normal work.
3. Keep a second Incognito/InPrivate window for permission/sharing tests.
4. Record browser/version, screen size, test date, target, release, detector, frame IDs and result. Use PASS, FAIL, BLOCKED or NOT IMPLEMENTED. Save a screenshot for every failure and record its exact message.
5. PASS means the stated result was observed. An IRSA 502 is BLOCKED for fresh retrieval, even when error handling correctly passes. One brightness sample cannot pass a variability test. A downloaded FITS cannot establish scientific correctness by itself.

Worksheet columns: Case | Target/sequence | Action | Expected | Actual | Result | Screenshot/report URL.

## Establish reusable real data

**B01 — App shell.** Refresh the home page. Open/close Help, Sources & methods and Investigations. Toggle the theme. Expected: readable layout, working navigation, no fictional sky or success message before data exists.

**B02 — Known cached field.** Open http://127.0.0.1:8000/?sequence=3122bdf8-1727-44ff-ad8c-aac23cffe151 in the QA profile. This local installation has used that real eight-exposure field in regression tests. Expected: images, dated timeline, frame count and SPHEREx DR1 metadata. If the ID is unavailable in another installation, use an existing real sequence from an investigation or load one successfully before continuing. Do not mark dependent image tests failed merely because their data prerequisite is missing.

**B03 — Live search/resolution.** Resolve NGC 1760, then inspect Coordinates & filters. Expected: about RA 74.08667°, Dec −66.53694°, resolver identity and epoch warning. Resolve an intentionally unknown string. Expected: clear rejection, no use of stale resolved coordinates. Test each preset: Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae and R Draconis. Name resolution and observation download are separate checks. Then Load observations. Expected: a real sequence or a specific, honest no-data/partial/error state. A 502 does not mean no observations exist.

**B04 — Manual coordinates and validation.** Enter valid decimal RA/Dec, then choose sexagesimal units and use equivalent coordinates. Resolve/load results should describe the same field within displayed precision. Try RA 400, Dec 95, blank coordinates and RA 24:00:00 in hour-angle mode. Expected: rejection before archive work, no crash or unrelated image presented as a new result.

**B05 — Request geometry.** On a loaded field, choose 3′, 6′ and 12′ presets. Also enter a rectangular 12 × 6 arcmin request. Before Load, expected: pending-field warning and unchanged loaded image. After a successful Load, expected: requested full dimensions and WCS-derived output shown separately. At 6.2 arcsec per display-grid pixel, 6′ is approximately 58 pixels; 12′ approximately 116. Requested size, returned native footprint and valid-data percentage are distinct. Existing low-resolution data must not become sharper by relabelling or hidden enhancement.

**B06 — Release, detector and dates.** Choose DR1 versus QR3 and detectors 1–6 separately. Enter a date interval drawn from the Observation log and Load. Expected: loaded provenance matches the request, dates obey the interval and the UI identifies pending versus loaded selection. Empty results are legitimate; changing detector or release must not silently keep old images labelled as new. Reuse the cached field after live tests if needed.

## Viewer and time controls

**B07 — Fit/native/zoom/pan/reset.** Click Fit Image; the complete loaded footprint should fit with unchanged proportions. Click Native Pixels; one loaded grid pixel should occupy one CSS pixel. Zoom in/out and drag in Pan mode. Expected: bounded movement, no stretching, coordinate/scale information stays coherent. Reset restores the view. Native grid pixels are not necessarily unresampled detector pixels.

**B08 — Orientation, cursor, target and fullscreen.** Move over the loaded sky image and then outside it. Expected: celestial readout only where appropriate, north/east labels and explicit outside-boundary feedback. Pan away; click Target. Expected: searched reference recenters if inside the loaded field or a clear out-of-field explanation. Toggle target marker. Enter/exit fullscreen; image proportions and controls should survive.

**B09 — Playback.** Press Next/Previous and keyboard arrows, drag the timeline, Play/Pause, change interval and toggle Loop. Expected: image, index, date, Evidence and timeline move together. Pause stops changes. Loop wraps when enabled; playback stops at the end when disabled. Read the true earliest/latest dates and baseline; frame count alone is not temporal coverage.

**B10 — Four comparison modes.** Choose Single exposure, A/B blink, Side by side and Swipe comparison. Change Compare B, pan/zoom and contrast. Expected: single means one exposure; blink alternates A/B; side-by-side retains undistorted geometry in both panes; swipe reveals the two registered inputs. Read wavelength-comparability warnings. A visible difference is not automatically motion or variability.

**B11 — Display and copied view.** Open Display, toggle nearest/smooth interpolation, change contrast and Reset contrast. Choose a non-first frame, a different B frame, zoom and pan. Copy view link into a new tab in the same profile. Expected: cached field, frame, comparison, pan, zoom and contrast restore. Display changes must not change exported measurement values. Full workbench-result restoration is not yet accepted. Main viewer currently provides asinh, not a complete linear/log stretch selector.

**B12 — Panel persistence.** Mark a position; note frame, coordinates, zoom and pan. Open/close Observations, Analysis, Evidence and Advanced workbench. Expected: the selected source and viewport persist. Evidence should be collapsed by default on initial load.

## Selection, evidence and apparent motion

**B13 — Observation log/provenance.** Open Observations, select a row and open Evidence. Expected: matching date, observation ID, mission, release, units, coverage, flags and original/archive download links. Unknown alignment residuals should say not assessed, not zero. Download native and display-grid FITS; verify nonempty files. Header/data validation requires a FITS-capable tool or developer tests, not browser appearance alone.

**B14 — Candidate notebook.** Click Mark and select a point. Choose classification, enter a QA note, Save annotation. Reload/reopen in the same profile. Expected: note, position and dated frame association persist. Mark another frame. Expected: marks belong to their selected frames. Avoid Clear annotations on existing investigations.

**B15 — Rectangle/circle.** Open Analysis, choose Rectangle, drag within the loaded image. Pan/zoom and switch panels. Expected: selection stays anchored to the sky. Click Load selected region explicitly. Repeat with Circle. Expected: bounded celestial request; circle uses its bounding rectangle. Drawing alone must not silently replace imagery. Very small/out-of-range requests should be rejected clearly.

**B16 — Manual motion and Follow.** Save exactly one QA association per frame in at least two distinct dated frames. In Analysis choose Manual apparent motion, set assumed positional error and Request motion fit. Expected: units, dates/baseline, fitted offsets/residuals and manual-association warnings. Enable Follow manual marks and step frames; expected recentering on the marks, pause on absent/ambiguous marks, and original fixed-sky viewport restored when disabled. These QA marks test the interface, not real object identity or motion.

## Spectral–temporal workbench

**B17 — Initial state/channel definitions.** Open Advanced workbench and expand Wavelength, extraction settings, tables and provenance. Expected: unmeasured light-curve selector explains Extract Spectrum first, 102 defined channel indices, explicit wavelengths/detectors and disabled blank zero-based channels 50/51. Six detector entry buttons distinguish loaded/cached from not queried. Unqueried must not mean zero coverage.

**B18 — Native spectrum.** Mark a source whose aperture and background annulus fit inside valid coverage. In expanded controls choose included frames and set radius < background inner < background outer in arcseconds. Click Extract Spectrum. Expected: progress/cancel state, then accepted measurements or precise exclusions. Inspect spectrum/table, dates, mJy units, formal uncertainties where supplied, flags and original links. Negative flux remains negative; nonpositive flux must not receive an invented magnitude or upper limit. All exclusions means this data/parameter combination failed, not a successful spectrum.

**B19 — Linked coverage and brightness history.** Inspect the time × wavelength matrix; click an observed cell or spectral datum. Expected: contributing dated frame opens. Select a group in the brightness-history dropdown. Expected: only matching proxy-band samples ordered by actual dates. A one-sample group is a point, not evidence of a change; two or more comparable dated samples are required to test the multi-epoch workflow. Failed/unqueried intervals must not appear as measured zero. Full calibrated response equivalence is not established.

**B20 — Spectrum comparison/exports.** Keep spectrum for comparison, mark a second position and extract. Toggle Normalize display only. Expected: labelled comparison preserves source coordinates/dates and raw exported flux. Download Analysis JSON and Measurement CSV; open them and compare rows, units, uncertainties and exclusions against the table. Clicking a contributor should return to its original observation.

**B21 — Reference mosaic and wavelength playback.** Choose a nonblank channel and Load mosaic reference. Expected: registered reference field, wavelength, valid coverage, original/private product links and no invented observation date. Request another channel, then Play cached wavelengths. Expected: channel changes, dated playback remains separate and playback does not fetch new archive planes every step. Pan reference beyond its boundary with neighbouring-field loading enabled; expected bounded loading with updated coordinates, never a fixed tile drawn at unrelated coordinates. Full progressive all-sky viewer acceptance remains incomplete.

**B22 — Detector combining.** Choose a detector/channel and Combine selected detector. Expected: within-detector mean with contributors, weights, effective wavelength and missing-pixel coverage. It is a broad spectral combination, not one monochromatic exposure or an increased-resolution image. Repeat detectors separately if archive access permits. A failed group must not be counted as one of six successfully constructed groups.

**B23 — RGB combining.** In expanded controls scroll to RGB combining / infrared false colour. Set Red 62, Green 34, Blue 0 (the current defaults), then Load infrared RGB mosaic. Expected: an actual three-channel result with channel/wavelength legend, disclosed independent stretching and transparent missing common coverage. Download provenance/FITS. Repeat with a duplicate or blank channel: expected validation rejection. RGB is an undated infrared visualization, not natural colour, an epoch stack or calibrated source spectrum. A successful request at one field does not establish all-sky coverage.

**B24 — Mosaic aperture quick-look.** Load reference channels for the same footprint and request mosaic aperture extraction in controls. Expected: wavelength/flux samples and gaps, explicit lack of propagated uncertainty, no invented SNR/errors/dates and no temporal curve. Do not interpret reference planes as independent observing epochs.

**B25 — Stack.** Select two or more independent dated frames that pass the selected-position wavelength check and valid aperture/background checks; click Stack included frames. Expected: explicit contributors, method/warnings, preview and derived FITS. Test incompatible/insufficient inputs too: expected rejection rather than misleading combined output. Current image variance omits annulus-estimation uncertainty and spatial covariance; calibrated PSF/response acceptance remains open. If no compatible pair exists, successful stacking is BLOCKED for that dataset, while correct rejection can PASS.

**B26 — Difference.** Choose distinct A/B observations with compatible response proxy; click B − A residual. Expected: original A/B, zero-centered signed residual, masks and variance/provenance download. Swap inputs and repeat: same-input arithmetic should reverse sign on the same valid pixels, without independent display stretches being mistaken for numeric evidence. Incompatible bands should be rejected. PSF matching, calibrated scaling and measured alignment residuals are not established, so a residual is not proof of variability.

## Reference context, jobs and failures

**B27 — Gaia DR3.** In Evidence → Reference context, Query Gaia DR3. Toggle visibility, adjust opacity and expand source details. Expected: optical markers, IDs, reference epoch, available proper motions/magnitude and unpropagated-position warning. Save the completed query with a report and check its source table. Proximity alone does not identify an infrared counterpart; optional epoch propagation is not implemented.

**B28 — WISE.** In expanded workbench controls click Load AllWISE W2 reference (4.6 um). Toggle overlay/opacity. Expected: distinct WISE labels, acquisition/coadd provenance and units; SPHEREx remains identifiable. No direct cross-survey brightness or counterpart claim. Live upstream failure is BLOCKED for retrieval, not PASS. New WISE processing has controlled tests; fresh live acceptance remains necessary.

**B29 — Metadata refresh.** Expand Release metadata refresh and request refresh with incremental on, then off if needed. Expected: release-aware metadata counts/data-through, queried/unqueried bounds, incremental overlap where previous data exists and explicit changed URLs. Existing reports/inputs must remain unchanged. Automatic scheduled refresh and changed bytes at the same URL are not fully accepted browser features.

**B30 — Cancel/retry/stale requests.** Begin a fresh request and Cancel while queued/running. Expected: cancellation status and preserved loaded evidence. If an archive 502 occurs, expected: bounded automatic metadata retries followed by inline Retry request; the previous field remains labelled as the previous field. Retry should submit the current explicit form and clear the notice when beginning. If upstream still fails, fresh retrieval remains BLOCKED. Start field A then change to field B: a late A response must not overwrite B. Do not repeatedly enqueue jobs; session limits can legitimately return 429.

**B31 — NEOSSat separation.** Select NEOSSat native workspace and load real native observations if available. Expected: native raw/counts labels, infrared detector/release controls disabled appropriately, native pixel readout and no invented celestial WCS/IR spectrum. Check raw playback/log/provenance. SPHEREx workbench should not apply spectral extraction to NEOSSat. Treat unavailable archive data as BLOCKED.

## Reports, downloads and permissions

**B32 — Immutable report and revision.** Return to your QA SPHEREx sequence, select a non-first frame, save QA notes and completed analyses, enter a unique investigation title and Save evidence report. Open Investigations → Open report. Expected: matching frame identities, notes, selected settings, warnings and pinned analysis tables. Change a note in Explorer; the original report must remain unchanged. Continue as a new revision and save; expected separate revision with original retained. Exact full interactive workbench restoration remains incomplete.

**B33 — Exports.** From the report download JSON, Annotated PNG and Dated animation; Print/save PDF. Expected: JSON matches snapshot; PNG uses the snapshot-selected non-first frame and only its annotations; GIF has chronological dated frames; printed report includes warnings/provenance. Open downloads, do not just check the button. FITS structural, WCS, unit and numeric validation requires developer/FITS-tool checks.

**B34 — Sharing/revocation/private products.** In Investigations create a read link. Open it in InPrivate: expected report and permitted pinned analysis products, no owner/edit controls. Before sharing, an owner-only analysis URL in InPrivate should be denied. A read token should authorize only products pinned to that report. Revoke read links in the owner profile; refresh the shared page and token-authorized product in InPrivate: expected denial. Do not expect public original archive files to become private when a report is revoked.

**B35 — Embed/review.** For a shared URL `/shared/TOKEN`, open `/embed/TOKEN` to inspect the read-only embed view. Expected: evidence/warnings, no editing or application script controls. Actual framing from an external site requires an explicitly configured allowed origin; a standalone page does not prove that policy. Independent-review persistence has no accepted end-to-end browser flow; do not mark it passed because a backend route exists.

## Usability and broader acceptance

**B36 — Screen sizes and keyboard.** Repeat core image/playback/panel tests at 1366 × 768, 1920 × 1080 and 390 × 844 using browser responsive mode. On desktop image/timeline should remain visible; on mobile panels may overlay. Expected: no page-wide horizontal overflow, unreachable actions or distorted comparison images. Use Tab/Shift+Tab/Enter, check visible focus/labels, and test theme readability. Physical touch/pinch, assistive technology, reduced-motion and long-duration performance need separate real-device/accessibility testing; responsive emulation does not prove them.

**B37 — Browser diagnostics (optional but useful).** Open F12 → Console and Network. Reload, pan/zoom, play, make an explicit request and save a report. Expected: no uncaught JavaScript errors, no fresh time-viewer archive search on every drag/wheel, appropriate HTTP error states. A blocked external request should not erase existing evidence. Record request path/status and job ID, not session cookies or private read tokens, in bug reports.

## What cannot pass from browser clicking alone

Planned or incomplete: work/transfer estimates; calibrated full response/PSF/deblending; complete decoded flags/selected-region comparison; catalog epoch propagation/counterpart ambiguity lists; optional Aladin integration; trial-motion shift-and-stack; optional source-detection suggestions; validated training activities; all stretch modes; arbitrary wavelength-range/coverage-brush controls; fully restored interactive investigations; scheduled ingestion and full changed-byte tracking.

Developer/operations checks still needed: numerical photometry/variance/WCS reference comparisons, product checksums, malformed API payloads/UUIDs, race/fault injection, quotas/queue recovery, persistent storage, backup/restore, logs/metrics/health and Linux/PostgreSQL/Celery/deployment. A browser pass never substitutes for these. See WORKBENCH_VERIFICATION.md for checks actually performed and FEATURES.md for all 78 requirement IDs.

## Final acceptance decision

Run every applicable B01–B37. Count results by category. List blocked tests with their missing data/service prerequisite and retry date; list unavailable requirements separately. The site is ready for a limited demonstration only when the intended demonstration flows pass and their limitations remain visible. Do not declare the entire requested scientific product complete while required tests are blocked or features remain unimplemented.
