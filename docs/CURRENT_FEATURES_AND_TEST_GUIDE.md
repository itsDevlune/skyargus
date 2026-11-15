> **Update:** This is the historical pre-fix audit. Its AUD-01–08 product defects have since received targeted fixes and regression checks; see [WORKSPACE_FIXES.md](WORKSPACE_FIXES.md). Current counts: 42 Python tests, 5 browser tests, 12/12 API audit. Upstream availability and unfinished science features remain separate.

# Current application audit and feature test guide

Tested 15 November 2026, on the local Windows application at **http://127.0.0.1:8000/**. This report describes current behavior, including failures; it is not a full-release certification. Application code was not changed during this audit. New audit scripts and evidence were added.

## Results

| Check | Result |
|---|---|
| Existing Python tests | **29 passed** |
| Existing formal Playwright tests | **3 passed** |
| Expanded browser audit | **34 checks: 29 passed, 4 product failures, 1 live Gaia failure** |
| Additional API/validation audit | **12 checks: 7 passed, 5 failed** |
| Ruff, Django system checks, migration drift check | Passed |
| Compiled Tailwind build | Passed |
| Real-data integration script | Passed: manual motion job, report save/reopen, PNG/GIF export, native NEOSSat playback, no JavaScript errors |
| Linux, Docker, PostgreSQL, Redis/Celery, production HTTPS, backup restore | **Not tested in this environment** |

These checks overlap; do not add their totals as independent feature coverage. The existing automated tests pass despite defects discovered by the broader audit. All 78 retained feature/resource IDs remain separately tracked in FEATURES.md.

Evidence: [browser results](evidence/application-audit/results.json), [API results](evidence/application-audit/api-results.json), [real explorer screenshot](evidence/application-audit/explorer-gaia.png), [native mobile screenshot](evidence/application-audit/native-mobile.png), [generated report PDF](evidence/application-audit/report.pdf). The explorer screenshot was captured after the Gaia failure; it does **not** prove a successful live overlay.

## Wave 2 follow-up, 2026-11-15

The focused offline Playwright suite now passes all 14 tests, including new mocked regressions for A/B blink, side-by-side aspect ratio, swipe, shared-stretch reset, and Gaia overlay visibility/upstream errors. The side-by-side aspect distortion (AUD-01) and malformed-UUID HTTP 500 behavior (AUD-06) have since been fixed; AUD-01 is covered by a mocked non-square preview test and AUD-06 by the re-enabled API validation tests. The Gaia test uses a mocked completed job and does not establish current ESA availability. No manual browser review or live Gaia/archive request was performed for this follow-up. Playwright's configured server used the existing `.venv313`, which currently reports Python 3.12.5 rather than the documented Python 3.13.15.

## Start the application

From the project directory, use two terminals:

```powershell
# Terminal 1
.\.venv313\Scripts\python manage.py runserver 127.0.0.1:8000

# Terminal 2
.\.venv313\Scripts\python manage.py workjobs
```

The server and local worker were already running during this audit. Do not start duplicate local workers. SQLite is the local database; Celery is intended for Linux production and was not tested here. If starting from a fresh installation, follow DEPLOYMENT.md for dependency installation, migrations and static asset compilation. Preserve local.sqlite3 and data/.

## Reliable starting field

Use these values to exercise the already-downloaded real-data workflow without requiring a fresh archive download:

| Field | Value |
|---|---|
| Workspace | SPHEREx |
| Units | Decimal degrees |
| RA | `269.452075` |
| Dec | `4.693391` |
| FOV width × height | `6` × `6` arcminutes |
| Release | DR1 |
| Detector | **3** |
| Dates | Leave both blank |

Click **Load observations**. Expect **8 real dated frames**, August 15–18, 2025, with observation IDs and downloadable FITS files. The initial detector default is 1, so explicitly choose 3. This is a field near a reference position, not a claim that the marked center is Barnard's Star's propagated 2025 position.

Direct cached links on this workstation:

- SPHEREx: `http://127.0.0.1:8000/?sequence=3122bdf8-1727-44ff-ad8c-aac23cffe151`
- NEOSSat: `http://127.0.0.1:8000/?sequence=170f3e57-b16a-48b7-8cb6-818bb55dfd32`

These IDs refer to the current local database and are not portable to a clean installation. The report/native data are public scientific cache objects; private notes still depend on your browser session.

## Current features and how to test each

### Search and data loading

| Feature | How to test | Expected/current result |
|---|---|---|
| Decimal RA/Dec entry | Enter the starting field above and load; try RA `360`, Dec `91`, or nonfinite values through the API | Normal field loads; invalid decimal ranges/nonfinite coordinates return 400. Passed. |
| Sexagesimal coordinates | Choose **RA hours · Dec degrees**, enter `17:57:48.498` and `+04:41:36.2076`, detector 3, FOV 6×6 | Resolves to approximately the same field. Conversion is implemented and unit-tested. **Boundary bug:** `24:00:00` is accepted due to floating-point conversion. |
| Object-name resolution | Enter a name and click **Resolve** | RA/Dec update; canonical name, resolver and epoch limitations appear. All five preset resolutions passed live. It does not automatically load images. |
| Five target presets | Click Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae, R Draconis | Each resolved in this audit. Presets use live reference positions; useful images, current proper-motion positions and resolved binary components are not guaranteed. |
| FOV presets | Click 3′, 6′, 12′ | Both width and height change. Passed. |
| Custom rectangular FOV | Enter width/height within 1–20 arcminutes, then explicitly load | Values affect archive selection, not display zoom. Bounds are tested; every valid rectangular configuration was not freshly downloaded. |
| Release and detector choices | Choose DR1/QR3 and detector 1–6 before loading | Choices are implemented. DR1 detector 3 was exercised with real images; all release/detector combinations were not tested live. **API bug:** numeric detector `3.9` silently becomes 3. |
| Date selection | Open **Date range & limits**; choose start/end and load | Reversed dates are rejected. **Known limitation:** “Through” end date is applied at midnight at its start, not the whole end day. Full inclusive-date behavior is unfinished. |
| Background loading/progress | Submit an uncached selection while a worker is running | A job/status URL and stage text appear; the web request does not process the FITS synchronously. The full worker pipeline is tested offline with a real FITS fixture. |
| Cancellation | Click **Cancel request** while queued/loading | Queued cancellation passed; unit tests also cancel during a download boundary. An in-flight upstream request may finish or time out before cancellation is observed. |
| Cache reuse | Load the starting field again | Reuses the stored sequence. No archive search is generated by pan/zoom. Passed. |
| Empty/error/partial states | See exclusion messages in a partial sequence; use offline outage tests rather than intentionally stressing archives | Backend tests verify no invented frame on outage. Every empty/single/partial UI variant was not independently covered in the expanded browser audit. |

### Viewer and Evidence Lens

| Feature | How to test | Expected/current result |
|---|---|---|
| Real cutout and observation log | Load the starting field; inspect the log and right-hand inspector | Real frame dates, IDs, source/release, units, coverage and warnings appear. Passed. |
| Previous/next and timeline | Click ‹/›; move the timeline slider | Frame number, image, date and Evidence Lens update. Passed. |
| Play/pause and speed | Select a speed and click ▶; click again to stop | Frames advance and then remain stopped. Passed. Speed is animation timing, not actual observing gaps. |
| Loop | Uncheck Loop, move to the final frame and play | Stops at the final frame. Passed. |
| Keyboard shortcuts | Click a non-input part of the page; press arrow keys or Space; repeat while editing Notes | Arrows step and Space toggles playback; typing fields are protected. Passed. |
| A/B blink | Select a comparison frame; choose **A/B blink**, then play | Alternates the chosen A/B observations. Passed. Different responses can mimic variability. |
| Side-by-side | Choose **Side by side** | Both images display, but **failed aspect-ratio check**: square frames become half-width while retaining full height. Do not use it for visual shape comparisons until fixed. |
| Swipe | Choose **Swipe comparison** and move the swipe slider | The dividing region changes the displayed A/B contribution. Passed. |
| Zoom/pan/reset | Click +/− or wheel; drag in Pan mode; click Reset view | Display changes without new archive searches; reset restores position and zoom. Passed. |
| Sky cursor/orientation/scale | Move over a SPHEREx image; check north/east and 6.2″/pixel label | Celestial mapping is implemented. Three positions passed high-DPI roundtrip checks. Alignment residual is still “not assessed”. |
| Fullscreen | Click ⛶ and exit fullscreen | Passed in Chromium. |
| Display contrast | Move Display contrast and click Reset | Appearance changes; original FITS identities do not. Passed. This is not recalibration. |
| Evidence Lens | Step frames and read inspector | Dates, mission/release, IDs, units, field-center wavelength where available, raw flags, coverage and limitations are shown. Passed basic metadata checks. Quality overlays, selected-source response and measured alignment remain incomplete. |
| FITS downloads | Click Native FITS and Display-grid FITS/original links | Local original/aligned downloads returned valid FITS signatures. Native files retain archive data; display-grid FITS has no validated propagated variance. |

### Annotations and analysis

| Feature | How to test | Expected/current result |
|---|---|---|
| Mark a source | In single-frame SPHEREx mode choose **＋ Mark**, then click the image | A position is selected; enter Notes/classification and Save annotation. Passed. |
| Four classifications | Choose unsure, possible motion, brightness change or artifact | Stored with the mark. These are user classifications, not scientific confirmation. |
| Edit/delete saved marks | Click Edit, change note, save; then Delete | Revision increments and deletion affects only that private mark. Passed. Stale edits are rejected by API tests. |
| Annotation privacy/persistence | Reload the same sequence in the same browser; compare with an incognito session | Same-session notes persist; another session cannot edit them. API ownership checks passed. Clearing cookies loses editing access. |
| Manual apparent-motion fit | Save marks for the same proposed source in at least two distinct dated frames, enter an assumed positional error, click **Request motion fit** | A queued result returns east/north angular rates, assumed uncertainty, baseline and RMS; JSON export is available. Passed by the integration script. Audit marks were arbitrary test clicks, not a physical motion measurement. |
| Unsupported analysis rejection | Request `/api/v1/analyses` with `method:"spectrum"` | Returns 400 with an explicit unfinished-method explanation. There is no working spectrum/stack/difference UI yet. |

### Reference data and NEOSSat

| Feature | How to test | Expected/current result |
|---|---|---|
| Gaia DR3 catalog query | In SPHEREx open Reference context → **Query Gaia DR3** | Queued ESA `gaiadr3.gaia_source` query; gold source circles and visibility toggle when successful. **Live audit failed with a connection timeout to ESA.** Code and earlier saved query evidence exist; this run does not establish current upstream availability. |
| Gaia overlay visibility | After a successful query, toggle Show catalog overlay | Intended to hide/show catalog circles. Not verified in this live run because the query failed. Positions are J2016.0; propagation/counterpart popups are absent. |
| NEOSSat raw optical workspace | Open the direct cached native link above, or select NEOSSat and load a bounded field | Four genuine raw detector frames displayed. Release/detector controls become inapplicable; source and raw-ADU labels are explicit. Passed cached workflow; fresh CADC discovery was not rerun in this audit. |
| Native-frame playback | Step/play the cached NEOSSat sequence | Dated detector frames advance. Passed. It does not establish sky registration or sky motion. |
| Unsupported native sky marking | Choose Mark and click a NEOSSat image | Explains that validated celestial mapping is unavailable; motion panel is hidden. Passed. |
| Native cursor feedback | Move inside the NEOSSat image | EX-13 follow-up now reports display-pixel coordinates and keeps celestial WCS unavailable; focused E2E regression is added but not yet run. |

### Investigations, reports, sharing and exports

| Feature | How to test | Expected/current result |
|---|---|---|
| Save immutable report | Give the investigation a title and click Save evidence report | Captures manifest, settings, annotations, warnings and completed motion results in JSON. Passed. |
| Investigation list/reopen | Click Investigations → Open report | Private report list and readable report appear. Passed. |
| New immutable revision | On a private report click **Continue as a new revision**, edit the title/notes, save | Revision 2 is created; revision 1 is unchanged. Passed. It does not fully restore all previous display settings. |
| Revision conflict protection | Try creating another child of revision 1 after revision 2 exists | API returns 409. Passed. PostgreSQL simultaneous-writer behavior has not been tested. |
| JSON export | Investigations → Export JSON, or report → Export JSON | Complete snapshot is returned. Passed. Keep this before losing browser-session access. |
| Annotated PNG | Open private report → Annotated PNG | A valid PNG downloads. **Updated:** exports the frame selected when this report revision was saved, with only its matching annotations. Save a new revision after changing the selected frame. |
| Dated GIF | Open private report → Dated animation | Valid multi-frame GIF downloads with date/source captions. Passed signature/integration checks. Fixed 1200 ms timing; viewer playback speed is not exported. |
| Print/PDF | Open report → Print / save PDF | Printable report exists; automated PDF generation succeeded. Full browser/OS print-dialog behavior was not tested. |
| Read-only sharing | Investigations → Create read link; paste in incognito | The shared report loads while its private API URL remains inaccessible. Passed. Link creation is explicit. |
| Revoke sharing | Investigations → Revoke read links; refresh the incognito link | Returns 404. Passed. Previously downloaded copies cannot be retracted. |
| Read-only embed | Replace `/shared/` with `/embed/` in a valid read link | Script-free report template with no edit controls, POST rejected, same-origin framing policy. Passed. Embedding from another website is intentionally blocked by current CSP. |
| Independent review records | Use the review API described below | Separate records work through the API; no review-entry UI is implemented. Owner-session API test passed; “independent session” is not verified personal identity. |
| Coordinate/view links | Click Copy view link and open it in a new tab, then explicitly load if only coordinates were supplied | Frame, mode, zoom, pan and contrast are serialized by the current client. EX-12 now reapplies pan after sequence loading and bounds it to the loaded patch; a focused browser regression is added but not yet run. Restored B selector can still disagree with the active B frame (AUD-02). |

### Interface and operations

| Feature | How to test | Expected/current result |
|---|---|---|
| Light/dark theme | Click ◐, reload | Theme switches and persists locally. Formal browser test passed. |
| Help | Click ?; close dialog | Quick-start instructions work. Passed. |
| Mobile layout | Resize to 390×844 or use browser device emulation | No horizontal page overflow in tested views; panels stack. Passed. This is not a full touch-device/accessibility certification. |
| Reduced motion | Enable OS/browser Reduce motion, reload | No initial autoplay; CSS transitions honor reduced motion. Passed basic check. |
| Sources/methods | Open Sources & methods | Source roles, limitations, acknowledgements and NASA notice are available. Passed. |
| Health endpoint | Open `/health/` | Returns JSON status and database connectivity. Local SQLite check passed. |
| Durable jobs and offline numerical work | Run Python tests | Real-fixture processing, duplicate task delivery, cancellation boundary, outage-without-fake-data, coordinate/WCS mapping, numerical stacking kernel and motion kernel pass. A tested kernel alone is not a finished scientific product feature. |

## API-only review example

In browser Developer Tools → Console, while signed into the owning browser session:

```javascript
async function argusPost(path, data) {
  const csrf = document.cookie.split('; ').find(x => x.startsWith('csrftoken='))?.split('=')[1];
  const r = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf || ''},
    body: JSON.stringify(data)
  });
  return {status: r.status, data: await r.json()};
}
const list = await (await fetch('/api/v1/reports')).json();
const reportId = list.reports[0].id; // Save a report first.
await argusPost(`/api/v1/reports/${reportId}/reviews`, {text: 'My separate review notes'});
```

For another session, the reviews route requires a valid `?share=TOKEN` for that report. Review agreement is not scientific confirmation.

## Historical audit findings and exact reproduction

No fixes to these product defects were applied as part of this testing/reporting request.

| ID | Severity | Reproduce | Actual result / impact |
|---|---|---|---|
| AUD-01 | High, scientific display | Historical: load square SPHEREx frame → Side by side | Fixed in `static/src/js/explorer.js`; the 2026-11-15 mocked Playwright regression verifies aspect preservation with non-square previews. Real-observation visual acceptance remains pending. |
| AUD-02 | Medium | Open cached sequence URL with `frame=2&b=1&mode=swipe&zoom=2` | Active B index is 1, but B dropdown shows index 7. Changing the dropdown can unexpectedly change the comparison. |
| AUD-03 | Medium | Set contrast 1.8, pan, click Copy view link, inspect/open link | Historical audit reported omitted state, but current source serializes contrast/pan. EX-12 adds pan restoration and clamping; re-run browser acceptance to close this finding. |
| AUD-04 | Low | Move pointer over native NEOSSat image | Historical audit found false outside-boundary feedback. EX-13 follow-up adds a native display-pixel readout; browser regression pending. |
| AUD-05 | Medium | Sexagesimal RA `24:00:00`, Dec `0:00:00` | Accepted as 359.99999999999994° and queues work, rather than rejecting an out-of-range hour value. Audit-created requests were cancelled. |
| AUD-06 | Medium | Historical: POST reports or candidates with `sequence:"not-a-uuid"` | Fixed: body UUID validation now rejects malformed sequence IDs as client errors; report/candidate regression tests are enabled and pass. |
| AUD-07 | Medium, evidence validation | POST a candidate with valid sequence/frame but RA=0, Dec=0, outside this field | Returns 201; outside-footprint annotation accepted. The audit removed only its own test mark afterwards. |
| AUD-08 | Medium | API numeric `detector:3.9` | Silently converted to detector 3 instead of rejected as an invalid enum. |

External failure EXT-01: Gaia's live ESA request failed with a connection timeout. It remains a network-dependent implemented capability, not a passed current data-integration check. No repeated load was sent to that archive to force a pass.

Additional code-confirmed limitations: end date is not whole-day inclusive; native/display-grid quantitative uncertainties are not fully propagated; report PNG always chooses first frame; view restoration is partial. A full security/performance audit was not conducted.

## Not currently implemented as complete user features

The app does **not** currently provide validated calibrated spectra/brightness charts, a complete 102-channel browser/coverage matrix, six detector composites, false colour or wavelength playback, quality-aware stack workflow, calibrated subtraction/residual inspection, Follow Mode, trial-motion stacking, source-detection suggestions, WISE imagery, Gaia epoch propagation/counterpart lookup, Aladin integration, drawn circular/rectangular cutout requests, full guided investigations, reviewed translations, automated source refresh/cache retention, or a tested production deployment/backup restore. These remain in the retained feature ledger. Some foundations exist, but they are not complete end-to-end features.

## Rerun commands

```powershell
.\.venv313\Scripts\python -m pytest -q
.\.venv313\Scripts\ruff check .
.\.venv313\Scripts\python manage.py check
.\.venv313\Scripts\python manage.py makemigrations --check --dry-run
npm run build
npm run test:e2e

# Web and worker must be running; uses cached real observations.
node scripts/verify_integrations.cjs

# Broad browser audit: five live name resolutions, one live Gaia query,
# private test reports/notes and sharing grants, screenshots and a PDF.
node scripts/audit-application.cjs

# Local API edge cases; cancels unexpectedly accepted validation work.
.\.venv313\Scripts\python scripts/audit-api.py
```

Audit scripts deliberately preserve and report failures, so inspect their JSON results rather than assuming an exit code of zero means every check passed. Routine pytest and formal Playwright tests are offline. Live archive failure is not evidence that local synthetic fixtures passed real integration.

## Current explorer redesign
See [EXPLORER_REDESIGN.md](EXPLORER_REDESIGN.md) for the new image workspace, manual instructions, WCS investigation, temporal selection policy, 58 passing Python tests, 11 passing browser tests and before/after captures. Earlier layout descriptions are historical. Stacking, subtraction and calibrated spectra remain unavailable.
