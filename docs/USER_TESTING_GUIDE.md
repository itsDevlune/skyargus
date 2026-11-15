# Argus: run locally and test as a user

Updated 15 November 2026. This guide covers the controls currently implemented in the repository. It distinguishes an operational UI from scientifically validated results. Record actual outcomes rather than assuming every test passes.

## 1. Start the application on Windows

Open PowerShell in the repository:

```powershell
cd C:\Users\Devanarayan\Downloads\nasaspaceapps\project\argus
$env:ARGUS_DEBUG = "1"
$env:ARGUS_DISPATCH = "local"
.\.venv313\Scripts\python.exe --version
.\.venv313\Scripts\python.exe manage.py migrate
.\.venv313\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Use the existing Python 3.13 environment. Migrations update the existing database; keep a backup before first-time upgrades. Do not delete local.sqlite3 or data/. Leave this terminal running.

Open a **second PowerShell terminal**, enter the same directory and start the local worker:

```powershell
$env:ARGUS_DEBUG = "1"
$env:ARGUS_DISPATCH = "local"
.\.venv313\Scripts\python.exe manage.py workjobs
```

Open <http://127.0.0.1:8000/>. Use that hostname consistently so session cookies and your private notes remain available. Stop each terminal with Ctrl+C when finished. Restart the web server after template changes if the old HTML remains visible; hard-refresh with Ctrl+F5 for changed CSS/JavaScript.

If dependencies are not installed, first run these setup commands from the repository (requires uv and Node/npm):

```powershell
uv python install 3.13
uv venv .venv313 --python 3.13
uv pip install --python .venv313/Scripts/python.exe --require-hashes -r requirements.lock
npm ci
npm run build
```

Do not recreate an already working environment unnecessarily. Do not copy production settings from .env.example for local HTTP: DEBUG=0 enables HTTPS/security requirements. Django does not automatically load .env here.

## 2. Test recording and preparation

### Master checklist — test every implemented feature

Use the numbered sections below for exact inputs and expected outcomes. Tick a box only after observing the result. Record unavailable dependencies as Blocked, not Pass.

- [ ] Initial empty workspace and no autoplay (S01).
- [ ] Object-name Resolve, failed lookup and five individual target presets (S03–S05).
- [ ] Decimal coordinates, sexagesimal coordinates and invalid coordinate rejection (S02, S06–S07).
- [ ] Custom rectangular FOV and each 3/6/12 arcminute preset (S08–S09).
- [ ] DR1 and QR3 release choices; all six detector choices (S10).
- [ ] Start date, inclusive end date and reversed-date rejection (S11).
- [ ] Explicit Load, pending-versus-loaded indicator and cancellation (S02, S12–S13).
- [ ] Source switching SPHEREx ↔ NEOSSat and disabled incompatible controls (N01–N02).
- [ ] Previous, next, timeline slider and observation-row frame selection (V01, E01).
- [ ] Play, pause, every speed, loop enabled and disabled (V02).
- [ ] Fit, Native Pixels, wheel zoom, plus, minus, pan bounds and Reset (V03–V04).
- [ ] Cursor coordinates, outside-boundary response, orientation and crosshair (V05).
- [ ] Single exposure, A/B blink, side-by-side, swipe and B-frame selection (V06).
- [ ] Swipe position slider at both extremes and midpoint (V06).
- [ ] Nearest and smooth interpolation; arcsinh, linear and log stretches (V07).
- [ ] Contrast slider, shared-contrast restriction and Reset contrast (V07).
- [ ] Target marker checkbox and return-to-target action (V08).
- [ ] HiPS Sky checkbox, Mosaic/Spectral mode and every available HiPS product choice (V09).
- [ ] Fullscreen enter/exit and Escape (V10).
- [ ] Copy view link and actual restored sequence/frame/comparison/viewport/contrast (V11).
- [ ] Arrow/Space shortcuts and typing without shortcut interference (V12).
- [ ] Observations panel, chronological IDs/dates, metadata and original-data links (E01).
- [ ] Partial-results notice, detailed failures and retry (F02).
- [ ] Evidence metadata, quality flags, comparability, coverage and provenance (E02).
- [ ] Native FITS and display-grid FITS downloads (R10).
- [ ] Pan versus Mark tool distinction; selected sky coordinates (E03).
- [ ] Classification options: unsure, possible motion, brightness change and artifact (E04).
- [ ] Save annotation, reload persistence, Edit and Delete (E04–E05).
- [ ] Clear annotations in a disposable session only (E05).
- [ ] Unsaved note, selected point and viewport retained between panels (E06).
- [ ] Gaia query, returned reference context, overlay visibility toggle and failure state (E07).
- [ ] Panel open/close, Escape and focus return (E08).
- [ ] Spectrum coordinates, aperture setting, extraction and output measurement table (A01).
- [ ] Spectrum JSON export inspected against displayed measurements (A01).
- [ ] Subtraction A/B selectors, result image and same-frame rejection (A02).
- [ ] Stack checkboxes, resulting contributors, coverage and incompatible-band rejection (A03).
- [ ] Stack FITS export opened and inspected (A03, R10).
- [ ] RGB R/G/B selectors, real colour result, channel mapping and duplicate rejection (A04).
- [ ] Motion error setting, two-frame fit, uncertainty/baseline and insufficient-mark rejection (A05).
- [ ] Motion JSON export inspected against displayed fit (A05).
- [ ] Investigation title, Save report and immutable confirmation (R01).
- [ ] Investigations list, Open report and provenance/annotation contents (R02).
- [ ] Continue as new revision; restored selection/settings and original unchanged (R03).
- [ ] Report JSON from both list and report page (R04).
- [ ] Annotated PNG: correct selected frame, annotations and footer (R05).
- [ ] GIF: every dated observation and correct sequence length (R06).
- [ ] Print/Save PDF: inspect all pages, images, notes and warnings (R07).
- [ ] Create read link and inspect read-only report in incognito (R08).
- [ ] Revoke read links; incognito refresh denied; owner report still available (R09).
- [ ] Explorer navigation, Sources & methods and agency acknowledgements (G01).
- [ ] Help dialog open/close and light/dark theme across pages (G01).
- [ ] Resolving, queued, processing, ready and Cancel states where applicable (F01).
- [ ] No coverage, single observation, upstream failure and missing saved cache (F03–F05).
- [ ] All five viewport sizes, open panels, reports and mobile navigation (section 10).
- [ ] Keyboard focus, 200% zoom, readable warnings and no console exceptions (section 10).

The underlying image/analysis artifacts may expose additional download links depending on the returned result. Test **every link actually displayed** and record its format and contents; absent results cannot be counted as tested exports. Planned capabilities in section 11 are not implemented features to tick as passing.

Use a normal browser window for your private investigation and an incognito window for sharing tests. Keep DevTools Console and Network available (F12). Enable Preserve log if helpful. Before each test note the browser, viewport, sequence ID, frame/date, request settings and any warning.

Use this record for each test:

| Test ID | Actual steps/input | Expected result | Actual result | Pass / Fail / Blocked | Screenshot/file |
| --- | --- | --- | --- | --- | --- |
| Example V03 | Fit, zoom repeatedly, drag right | Image moves within bounds | Fill this in | Fill this in | Path/name |

**Pass:** visible result and saved/downloaded contents match the expectation. **Fail:** wrong result, lost state, inaccessible control or unexpected error. **Blocked:** necessary archive/cache/network data unavailable. A 200 response or a button click alone is insufficient.

## 3. Reliable starting field

### Locally cached example (no name resolver needed)

Open this link on this installation:

<http://127.0.0.1:8000/?sequence=3122bdf8-1727-44ff-ad8c-aac23cffe151>

This saved sequence contains eight genuine SPHEREx observations in the current local test cache. IDs are installation-specific: on another machine the link may be unavailable. It should show a dated image, eight observations, a baseline, frame count and provenance. It must not fetch fabricated replacement imagery.

### Search example

1. Select SPHEREx infrared.
2. Open Request settings (older rendered templates say Coordinates & filters).
3. Choose Decimal degrees; enter RA `269.452075`, Dec `4.693391`.
4. Choose DR1, detector `3`, requested width `6`, height `6`; leave dates blank.
5. Click Load observations. Wait for the worker to finish.
6. Compare the displayed coordinates, requested footprint, returned WCS footprint, dates and coverage with the request and Observation panel.

Existing cache may return immediately; fresh archive requests require internet. Frame count can differ with archive availability/version. A known cached frame count is not a universal live-archive promise. Pixelated 58×58 data at 6.2 arcsec/pixel represent approximately six arcminutes; enlarging it does not add resolution.

## 4. Search and request tests

| ID | Steps and example | Expected user-visible outcome |
| --- | --- | --- |
| S01 | Open a clean `/` page | Empty workspace; no invented image or autoplay; navigation and search usable. |
| S02 | Perform the explicit search above | Correct loaded field, dated frames or truthful archive/no-coverage message; worker progresses beyond queued. |
| S03 | Enter `Barnard's Star`, click Resolve | RA/Dec populated, reference-position identity/warnings shown. Then Load to fetch observations. Resolution alone must not silently replace loaded evidence. |
| S04 | Resolve `this-object-does-not-exist-argus` | Clear error; stale resolved identity must not be presented as the new target. Restore explicit coordinates afterward. |
| S05 | Expand Example targets; try Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae, R Draconis | Each invokes resolution; coordinates/identity update or a truthful resolver error appears. Presets do not guarantee archive coverage. |
| S06 | Set hour-angle units; RA `17:57:48.498`, Dec `+04:41:36.208`; Load | Field close to decimal example (rounding allowed); units interpreted as RA hours, not degrees. |
| S07 | Try Dec `91`, RA `NaN`, width `0`, height `21`, RA hours `24:00:00` | Validation rejects invalid input; no usable result falsely attributed to it. Browser validation may prevent submission before the server. |
| S08 | Click 3′, 6′, 12′ presets, then custom width `6`, height `12` | Presets set both dimensions; custom rectangle stays rectangular. Editing shows pending request; old image remains the previously loaded field until Load. |
| S09 | Load the rectangular request | Requested and returned WCS dimensions roughly agree within pixel rounding; no unexplained 12′ request shown as 6′. Coverage is a separate value. |
| S10 | Change release DR1/QR3 and detectors 1–6, loading deliberately | Selection retained, labels/wavelength metadata correspond to returned products; missing coverage is reported. These are discrete selections, not continuous spectral tuning. |
| S11 | Set From `2025-08-15`, Through `2025-08-18` on the example | Loaded dates fall within the requested inclusive UTC range; count/baseline reflect returned sample. Try reversed dates and verify rejection. |
| S12 | Start a fresh request and click Cancel while working | Cancellation status; previous usable field preserved; late completion must not overwrite a newer field. Cached instant results may finish before Cancel can be exercised. |
| S13 | Change FOV without Load; pan/zoom | Pending indicator remains; no `/api/v1/searches` request from display gestures alone. Optional HiPS context requests are distinct. |

## 5. Viewer, time, display and wavelength tests

| ID | Steps | Expected outcome |
| --- | --- | --- |
| V01 | Next, Previous; drag timeline to another frame | Image, date, frame count, evidence and highlighted observation agree. |
| V02 | Play, change speed, Pause; toggle Loop at final frame | Frames advance at selected interval; pause stops; loop wraps only when enabled. Dates are real observation dates; gaps are not displayed to temporal scale. |
| V03 | Pan tool → Fit Image → zoom repeatedly until image exceeds both viewer dimensions → drag 40 px | Image moves in direction of drag within loaded boundary. At Fit, zero movement is expected if the full image already fits. Pointer release ends drag. |
| V04 | Wheel zoom, +/−, Native Pixels, Fit Image, Reset | Scale changes without retrieval; Native means one loaded-grid pixel per CSS pixel. Fit restores complete image; Reset recenters and resets its documented display settings. |
| V05 | Move pointer over image and outside it | Sky readout changes over celestial data; outside boundary is identified. N up/E left displayed where applicable. NEOSSat instead uses detector pixels. |
| V06 | Select comparison B different from A; choose blink, side by side, swipe; move swipe slider | Correct two dates/images compared; aspect ratios preserved; split changes; comparison warnings remain visible. |
| V07 | Change nearest/smooth interpolation, arcsinh/linear/log stretch, contrast and Reset contrast | Display visibly updates where supported; original downloads and scientific measurements remain unchanged. Shared comparison contrast can intentionally be disabled. |
| V08 | Target marker on/off; Target button | Marker visibility changes and target can be recentered. It marks reference coordinates, not necessarily the target's current apparent position. |
| V09 | HiPS Sky on/off; choose Mosaic/Spectral mode and each available HiPS layer | Explicit context/mosaic labels; available layer or median product changes. It is distinct from dated exposure playback; no claim of continuous 102-channel playback. |
| V10 | Fullscreen button; Escape | Viewer expands and exits without losing frame/selection. Browser fullscreen permissions may require direct user interaction. |
| V11 | With frame/B/mode/zoom/pan/contrast set, Copy view link; paste into same browser | Saved sequence reopens with linked state. Missing cache yields explicit message. Test actual restored values, not just clipboard text. |
| V12 | Arrow keys and Space with page focused, then while typing in notes/input | Frame stepping/playback works outside inputs and does not hijack text editing. |

## 6. Observations, evidence and annotations

**Additional telescope overlays:** Evidence → Reference context → Query Gaia DR3 / Query AllWISE. Gaia appears as gold circles; AllWISE as cyan squares. Toggle each visibility checkbox independently. Pan/zoom should move markers with the image. AllWISE is limited to 200 catalog sources; it is not a WISE image layer. An upstream error must retain prior loaded evidence and remain visible. Native NEOSSat pixels cannot accept a celestial overlay without validated WCS. Restart both server and worker after installing this feature.

1. **E01:** Open Observations. Click an observation row. Its date and image must agree with the viewer. Inspect wavelength, coverage and quality information. Open FITS download and archive-original links separately.
2. **E02:** Open Evidence. Check selected observation ID, date, mission, release, units, wavelength, coverage, flags, alignment/comparability warnings. Native and display-grid FITS are different products; preserve that distinction.
3. **E03:** Choose Mark, click the center of the celestial image. Evidence opens with finite RA/Dec. Pan must drag instead of creating a mark; marking must not accidentally pan.
4. **E04:** Choose classification `possible motion`; enter `Manual UI test — association not confirmed`; Save annotation. Confirm the mark card text, classification and frame. Reload in the same browser and verify persistence.
5. **E05:** Edit that test mark and save changed text. Delete only your own test mark and verify it disappears. Clear annotations is destructive for this session's annotations: use only a disposable test session, never existing user notes.
6. **E06:** Write an unsaved note; open Analysis/Observations/Evidence without reloading. The text, selected point, frame and viewport must remain. Unsaved text is not promised to survive a full browser reload.
7. **E07:** Query Gaia DR3 under Reference context; toggle Show catalog. Returned optical reference sources and overlay should match the selected field, or show a truthful network/no-results error. They are not SPHEREx detections or NEOSSat tracking results.
8. **E08:** Close panels using X and Escape; use Tab/Enter to reopen. Focus should return to opener when dismissed from inside. Long metadata must scroll without trapping essential controls.

## 7. Analysis actions (worker required)

### Actual 102-channel cube (separate from loaded-exposure atlas)

**Channel comparison and navigation:** After loading, select Channel A and Channel B from their full102-item dropdowns. Choose Single, A/B blink, Side by side or Swipe. Swipe split changes only the display boundary. Compared planes share percentile/asinh limits and one viewport; this is wavelength comparison, not a time-variability measurement. Wavelength slider/numbered grid selects A; B remains fixed.

Use Pan to drag; zoom enough that the tile exceeds the viewport before expecting movement. Plus/minus/wheel zoom; Fit shows the full tile; Native pixels is one loaded cube pixel per CSS pixel. Reset view recenters. Shared contrast and nearest/smooth interpolation affect both compared channels. Fullscreen cube expands this viewer. Choose Select spectrum pixel to extract at a point instead of dragging; side-by-side clicks map to the corresponding same-grid pixel. Play wavelengths steps A through actual102 channels, with interval/loop controls, independently of the dated-exposure timeline. Closing the panel stops playback and preserves viewport/selection. Blank channels remain blank and are still labeled unavailable.

The example field now has a fully downloaded genuine DR1 cube in this installation (tile7945). Its first load should reuse that cache once the worker is restarted. If another tile times out, repeat Load102-channel cube: completed verified chunks resume rather than restarting from zero. Expand panel to see the full102-channel grid. Extract at marked source / field position uses real WCS to sample the nearest mosaic pixel and reports that actual coordinate. Channels51 and52 are blank in the verified example. See REAL_CUBE_VERIFICATION.md and its screenshots/results.

1. Load a SPHEREx celestial field and open Analysis → Real 102-channel DR1 cube.
2. Click Load 102-channel cube. The first request downloads a genuine tile (~306 MiB); subsequent requests reuse its saved original. Web and workjobs must both be restarted after this update.
3. Inspect tile ID/date span/warning. Move the slider from 1 to 102: wavelength and image change together. Availability buttons show per-channel tile coverage; blank channels remain blank, not interpolated.
4. Toggle valid-pixel coverage: cyan means finite IMAGE with NHITS > 0, not a certified quality mask. Raw flags remain in the spectrum result.
5. Click a pixel or enter FITS X/Y (0–511), then Extract pixel spectrum. Verify the 102-row table, gaps and plotted values; export JSON. This native HPX image is not north-up; the backend reports the sampled sky coordinate through actual WCS.
6. Download original cube FITS and inspect IMAGE, NHITS, FLAGS and SPECTRAL_CHANNELS in a FITS-aware application. Match a few selected channel/pixel values to the UI table.

This is a mosaic surface-brightness spectrum with no supplied quantitative uncertainty; it is not integrated source flux or molecular identification. Full data retrieval depends on archive connectivity; an HTTP failure or transfer deadline must be reported as Blocked rather than successful cube exploration.

Open Analysis and select the tool. Run these against the genuine eight-frame cached example. If there is no current source selection, spectrum uses the entered/field coordinates. Wait for completion and inspect the actual result; retain all warnings.

| ID / feature | Example steps | What to inspect |
| --- | --- | --- |
| A01 Spectrum | Choose Spectrum; RA `269.452075`, Dec `4.693391`, aperture `3` pixels; Extract spectrum | Dated measurement table with wavelengths, flux/error and warnings; current local example previously returned six accepted measurements. Export spectrum JSON and compare rows/uncertainties to table. Count can change with different evidence or selections. This is quick-look aperture extraction, not calibrated ePSF spectrophotometry. |
| A02 Subtraction | Frame A first observation, B second; Compute difference | Real residual preview, frame identities, valid pixel counts and nominal-bandpass/comparability warning. Same frame twice must reject. A residual is not a confirmed variable source. |
| A03 Stacking | Select first and second observations; Stack selected frames | Preview, contributor count `2`, weights/mask/coverage/provenance description; download FITS where offered. Disjoint/unassessed nominal bandpasses may correctly reject. Do not call any rejected selection a successful stack. |
| A04 RGB | Choose three distinct observations for R/G/B (first, second, third); Generate RGB composite | Colour image plus actual channel dates/wavelength mapping; visualization-only warning. Duplicate channels reject. This is the RGB combining location; it does not improve spatial resolution or establish calibrated colour. |
| A05 Manual motion | Save marks on same candidate in frames 2 and 3; choose error `3.1` arcsec; Request motion fit | Finite east/north angular rates, time baseline, uncertainty/RMS and caveats. Export motion JSON and compare to displayed result. One mark should reject clearly. Manual associations do not establish identity, orbit or hazard. |

For every result, open offered preview/FITS links and inspect their content. Merely receiving “completed” is insufficient. A single-detector example is not a verified six-detector survey composite. Existing implementation may show tables rather than plotted graphs; do not expect an invented chart.

## 8. Investigation, sharing and every report export

1. **R01:** Select frame 2, a different B frame, contrast `1.5`, and a marked point. Enter title `My Argus user test`; Save evidence report. Expect immutable-save confirmation.
2. **R02:** Open Investigations → your report → Open report. Verify title, revision, actual frame IDs/dates, warnings, annotations and original-data hashes. Open image links and ensure real images load.
3. **R03:** Continue as a new revision. Verify restored frame, contrast, comparison/view settings and selection. Existing reports can only restore settings they originally saved. Make a change and save: expect new revision; original report must remain unchanged.
4. **R04 JSON:** Export JSON from Investigations or report. Open in a text editor; verify sequence IDs, settings, candidates, warnings and provenance match the report. Save the file outside the browser download temp area.
5. **R05 PNG:** Annotated PNG from private report. Open the image; selected frame must match the saved frame, annotation circles belong to that frame, and timestamp/provenance footer is readable. PNG metadata includes report ID, zero-based FrameIndex, observation ID and date. The PNG is an annotated evidence export, not a screenshot of every display control.
6. **R06 GIF:** Dated animation. Open in browser/image viewer; check all sequence dates, progression and frame count. Some OS preview apps display only the first frame; use a browser. Current example has eight frames.
7. **R07 PDF:** Print / save PDF. In print dialog choose Save as PDF. Open the saved file; inspect titles, warnings, images and notes across page breaks. PDF file existence alone does not verify content.
8. **R08 Share:** From Investigations create read link. Paste into incognito. Verify correct title, observations and notes, with no editing capability. Private report URL should not grant ownership to the incognito session.
9. **R09 Revoke:** In original browser revoke report read links; reload incognito share URL. Expect unavailable/404; old screenshot visibility in browser history is not a fresh authorized response. Original private report remains readable in owner session.
10. **R10 Downloads:** Test native FITS, display-grid FITS, stack FITS and archive originals wherever offered. A FITS file opens in a FITS-aware viewer (e.g. an installed scientific viewer), not a generic photo app. Confirm dimensions/header/provenance rather than renaming it PNG. Archive-original links may require internet even when local artifacts are cached.

Keep session cookies until exports are saved. Clearing cookies loses private editing access. Creating/revoking a share is separate from saving a private report.

## 9. NEOSSat, navigation and failure states

- **N01:** Source → NEOSSat optical raw. Release/Detector disable; guidance changes. Load a known cached NEOSSat sequence from this installation if available. Native detector readout, uncalibrated raw units and celestial-analysis restriction must remain explicit. An arbitrary sky coordinate is not guaranteed archive coverage.
- **N02:** Switch back to SPHEREx: Release/Detector re-enable; do not interpret an old image as the new unsubmitted source request.
- **G01:** Explorer, Investigations, Sources & methods, Help and theme controls work. Sources page retains agency acknowledgements and limitations. Help opens/closes via keyboard; theme changes all pages legibly.
- **F01:** Fresh request: observe resolving/queued/download/processing/ready as applicable. Cached requests can bypass stages. If queued forever, inspect worker terminal first.
- **F02:** Partially available result: one concise notice, usable frames retained, expandable technical failures, retry action. Retry can still fail while upstream is unavailable.
- **F03:** No coverage/single frame: truthful empty/single-observation state. Time comparison must not manufacture a second epoch.
- **F04:** Archive/resolver failure: understandable message, previous loaded evidence preserved. HTTP 502/503 is an upstream failure, not proof of local rate limiting. Offline DevTools tests may also block local APIs; label those as controlled failures, not actual archive outages.
- **F05:** Open a saved link whose sequence is unavailable: explicit unavailable message and retained linked coordinates/settings; no fabricated sky.

## 10. Visual and accessibility checks

Test 1920×1080, 1366×768, 1024×768, 768×1024 and 390×844 using DevTools device dimensions. At each size inspect initial page, loaded image, Request settings, Evidence, Analysis, Observations, Investigations, report, Help and Sources.

Pass criteria: no horizontal page overflow, hidden primary action, overlapping labels or stretched images; desktop timeline stays visible; mobile scroll reaches every supported control; dismissible panels keep forms usable. Inspect at 200% browser zoom. Tab through controls with visible focus; test Enter, Escape and Space. Ensure errors/warnings include text and no new console exceptions appear. Real touch gestures require a real touch test; mouse wheel does not prove pinch support.

## 11. Not currently complete: do not report as passing UI features

The feature ledger contains planned/incomplete work beyond the implemented controls: rectangle/circle sky-region drawing, full 102-channel browser/coverage matrix, continuous wavelength playback, calibrated ePSF extraction, complete six-detector survey combinations, and broader release/deployment acceptance. See FEATURES.md for exact status. A detector selector, static HiPS layer or quick-look result does not establish these capabilities.

## 12. Optional automated developer checks

These supplement manual UI acceptance:

```powershell
.\.venv313\Scripts\python.exe -m pytest -q
.\.venv313\Scripts\python.exe -m ruff check apps argus science tests
npx playwright test --workers=2
node scripts/ui-roundtrip.cjs
```

The round-trip script creates private test annotations, immutable reports, analysis jobs and share/revocation records from cached data; it is not read-only. It saves evidence under docs/evidence/ui-roundtrip/. Run it only when you want those test records. Known repository-wide Ruff findings in docs/evidence/workbench/aperture_photometry.py are I001 and two F841 findings; application-only lint and repository-wide lint are different checks.

## 13. Troubleshooting

| Symptom | Check |
| --- | --- |
| Connection refused | Web terminal running? Correct port/path? |
| Port already in use | Reuse the existing intended server or stop it with Ctrl+C; do not launch several competing servers. |
| Queued indefinitely | Second workjobs terminal running from this repository with same environment/database? |
| HTTPS redirect on local HTTP | Set ARGUS_DEBUG=1 in web terminal and restart. |
| Name resolution unavailable | Use explicit RA/Dec example; record resolver test as blocked separately. |
| Saved sequence unavailable | Cache ID belongs to another installation or data removed; use explicit search, requiring upstream availability. |
| 502/503 | Inspect archive message; retain usable cached data; retry later. Do not claim success by hiding the error. |
| Old design still visible | Restart Django and Ctrl+F5; confirm correct server/worktree. |
| Pixelated image | Read data dimensions and pixel scale; zoom/interpolation changes display, not scientific resolution. |
| Save/continue failed | Preserve cookies; use owner browser; capture exact message and report/sequence ID. |

Finish by listing passed, failed and blocked test IDs with evidence. Report a reproducible failure with input, selected frame, expected/actual behavior, screenshot and console/network error. Do not include secret share tokens in public bug reports.
