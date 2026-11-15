
## 0. Current authorization and precedence

**Build the actual Argus web application. Planning and scaffolding are already a starting point, not the stopping point.** This instruction supersedes the earlier planning-only/foundation-only override and any project-document instruction requiring new authorization merely to begin the product milestones. Update those stale stopping instructions in the repository so they do not conflict with this task. Preserve existing user work and working code.

You are authorized to inspect, plan, implement, install project dependencies, run bounded public-data queries, test, fix defects, and prepare a production deployment within the available development environment. Do not purchase services, expose secrets, destroy user data, or publish externally without the necessary existing authorization/access. If deployment credentials are absent, deliver a working local application and reproducible deployment configuration, identifying exactly what remains.

Read this complete document and inspect the repository, including its instructions and current documentation. Do not restart an existing Django project unnecessarily. Verify reported previous checks instead of assuming they passed. Treat existing planning documents as context to reconcile, not as proof of implemented features.

Work through the phases below, implementing and integrating features. Do not stop after a plan, attractive screen, placeholder API, or scaffold. Each visible action must have working behavior. Every feature in the inventory must be tracked to evidence. A feature correctly rejecting unsuitable data can be valid behavior, but a permanently disabled feature is not a completed implementation.

Make routine engineering choices autonomously. Explain material decisions with concise rationale, alternatives, evidence and consequences; do not expose private internal deliberations. Surface actual blockers, work on independent tasks while blocked, and record an exact handoff if a session ends. Never claim complete delivery while required features remain unimplemented, blocked, or unverified.

## 1. What to build

**Argus helps people watch the infrared sky change and turn an interesting change into reproducible evidence.** It is a public-facing application for NASA Space Apps’ “Planet X and SPHEREx” challenge.

The main experience is a 2D sky cutout viewer. A visitor searches by object name or RA/Dec, selects a field of view, requests available SPHEREx observations, plays dated frames, marks a candidate, checks evidence and saves a report.

Use real SPHEREx observations as the central dataset. Add Gaia DR3 catalog context, WISE reference imagery, and a separate NEOSSat observation workflow using the provided CSA/CADC resources. All surveys must remain identifiable. Do not represent optical, infrared, catalog, and spacecraft-tracking products as interchangeable images.

The primary workflow is:

1. Search a named object or explicitly entered sky coordinates.
2. Show resolved identity/reference coordinates and select a bounded angular FOV.
3. Discover available observations and useful dates/wavelength coverage.
4. Load genuinely comparable aligned cutouts.
5. Play, step, blink or compare observations with dates always visible.
6. Mark a possible motion, brightness change, artifact, or uncertainty.
7. Inspect wavelength, quality, alignment and provenance through Evidence Lens.
8. Request supported analyses and save/export/share an immutable evidence report.

Keep the whole project unified. A previous four-person/agent assignment is obsolete. Separate runtime processes do not require separate microservice repositories.

## 2. Required resources and real integration responsibilities

Use every supplied resource according to its actual role. Reading a tutorial or linking an informational page is different from integrating a dataset. Maintain this distinction in the UI, source ledger and release report. Do not interpret “all resources” as mirroring entire archives or supporting every telescope in CADC.

| Resource | URL | Required use |
|---|---|---|
| NASA/IPAC SPHEREx hub | https://irsa.ipac.caltech.edu/Missions/spherex.html | Primary mission/archive entry point; current releases, explanatory documentation, calibrations and acknowledgements |
| Official SPHEREx tutorials | https://caltech-ipac.github.io/irsa-tutorials/spherex/ | Verify discovery/cutout/PSF workflows; adapt relevant code only under applicable terms; record notebook version/commit |
| WiseView | http://byw.tools/wiseview | Study the blink/time-viewing experience and credit inspiration; do not assume a public API or permission to copy its code/assets |
| Gaia mission data at MAST | https://archive.stsci.edu/missions-and-data/gaia | Implement a bounded Gaia **DR3** reference catalog overlay using a supported DR3 endpoint, with release and epoch labels |
| CSA NEOSSat mission information | https://www.asc-csa.gc.ca/eng/satellites/neossat/ | Mission explanation and attribution in the NEOSSat context/help section |
| CADC | https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/ | Verify a supported public access route for NEOSSat discovery/download; do not scrape or bulk-query every archive collection |
| CSA NEOSSat tutorial | https://github.com/asc-csa/NEOSSAT_Tutorial | Inspect methods, calibration assumptions, dependency/license terms and commit; adapt appropriate scientific workflow |
| CSA NEOSSat dataset | https://data.asc-csa.gc.ca/dataset/neossat | Resolve actual observation files/metadata and integrate a bounded real NEOSSat example plus supported search behavior |

Also use current SPHEREx data-access/product documentation:

- https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/
- https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/
- https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html
- https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources

### Resource verification rules

The preparation-stage documentation check found SPHEREx hub/tutorials, MAST Gaia, CSA mission information, CADC and the tutorial repository reachable. WiseView returned a gateway error and the CSA dataset page timed out. These were page retrievals only, not successful data integrations. Recheck all applicable interfaces and record the outcome. Do not perpetuate an earlier statement that the user has supplied no challenge resources: the complete resource list above is now supplied.

The challenge explicitly requests Gaia DR3. Pin DR3 rather than silently querying a provider's unversioned default. Verify the exact DR3 table/service: the provided MAST landing page must not be assumed to expose every DR3 product. A documented authoritative alternative access endpoint may be used and cited. Do not replace DR3 with DR2; if a newer release exists, record it without silently changing the requested baseline.

SPHEREx documentation currently identifies DR1/QR3 image access. Verify current names and schemas at implementation time. Do not blindly reuse old QR2 tutorial queries. Request dated exposures for motion/variability; a merged all-sky cube is not a dated exposure sequence.

For WISE reference context, use supported IRSA/other documented data services. WiseView can inform design but is not itself a promised backend. Keep band/epoch/resolution labels visible. WISE time-series functionality may be added using verified products, but must not substitute for the SPHEREx workflow.

NEOSSat has different passbands, sampling, pointing/tracking and calibration needs. Implement its adapter and processing policy separately. If a frame has inadequate celestial WCS, use the justified native-frame mode or a validated astrometric solution with uncertainty labels. Never invent registration, compare detector coordinates as sky motion, or infer hazards/orbits from manual marks. Do not promise NEOSSat coverage of the five SPHEREx targets.

### Attribution and terms

Retain this user-supplied notice on the Sources/About page:

> NASA does not endorse any non-U.S. Government entity and is not responsible for information contained on non-U.S. Government websites. For non-U.S. Government websites, participants must comply with any data use parameters of that specific website.

Include the exact required mission/dataset acknowledgements after checking their current wording. Preserve citations, survey release, original file links and tutorial licenses. Do not imply Argus is operated, certified or endorsed by NASA/CSA. Do not use agency logos as Argus branding without appropriate permission. Respect third-party access limits, attribution, redistribution and cache terms. CADC is a professional research facility: use bounded, cached access and review its service policies before exposing public query amplification.

## 3. Technology requirements

Use this stack unless a concrete compatibility/correctness problem justifies a documented substitution:

| Area | Selection and responsibility |
|---|---|
| Runtime | Preferred Python 3.13.18; verify the installed interpreter and supported deployment image |
| Application | Django 5.2 LTS, latest supported compatible patch; templates, ORM, validation, sessions, migrations and JSON endpoints |
| Astronomy | Astropy for FITS, coordinates, units, time and WCS; Astroquery for supported archive/catalog interfaces |
| Alignment | reproject with method-appropriate footprints/masks and uncertainty handling |
| Numerical work | NumPy and SciPy |
| Rendering | Pillow and astropy.visualization for previews; quantitative arrays remain separate |
| Measurement | Photutils for justified source/background/aperture/PSF tasks |
| Download | Requests with bounded streaming, connect/read timeouts and URL validation |
| Background work | Celery with Redis broker; PostgreSQL is authoritative for durable job status |
| Database | PostgreSQL and Psycopg for the release; SQLite may remain an explicit isolated local-development option |
| Frontend | Django templates, compiled Tailwind CSS, JavaScript ES modules, native Fetch and Pointer Events |
| Image interaction | Evaluate OpenSeadragon first for 2D pan/zoom/sequence rendering; combine with Canvas/SVG annotations as appropriate |
| Charts | Plotly.js, loaded only when opening analytical charts |
| Sky context | Aladin Lite for an optional reference-context view; main cutout exploration must work independently |
| Storage | Shared persistent files behind a storage abstraction; object storage when deployment requires it |
| Deployment | Docker Compose, Linux, Gunicorn and Nginx with HTTPS |
| Verification | pytest, pytest-django, Playwright and Ruff |
| Reproducibility | Python direct declarations plus a hash-pinned lock workflow such as pip-tools; package.json and npm lock |

OpenSeadragon is an image viewer, not a celestial WCS engine. Preserve the verified image-to-sky mapping yourself. If it cannot meet correctness/performance needs, record a measured decision and use the custom Canvas viewer. Do not maintain two competing primary viewers unnecessarily.

Validate versions/wheels in clean environments and test Linux separately from Windows. Do not claim a runtime version that is not installed. Preserve the user's existing environment; isolate project dependencies. Configure Celery under Linux/WSL2/containers rather than assuming native Windows support. Install dependencies by phase, not speculative unused packages.

Do not introduce React/Next, Flask/FastAPI alongside Django, a GPU requirement, a mandatory LLM classifier or a microservice rewrite without concrete need and a decision record. No AI API is required for Argus's baseline features.

## 4. Beautiful, minimal product UI

Build a polished scientific workspace that is understandable to a beginner and efficient for an experienced observer. It must feel like a coherent application, not a collection of demo cards.

### Visual direction

- Restrained observatory aesthetic: graphite/ink, neutral surfaces, readable typography and a single cool-blue primary accent.
- Support light and dark themes; the actual sky image keeps its appropriate image background and separate data contrast settings.
- Use system sans-serif or one self-hosted font; tabular numbers for coordinates/times. Comfortable line spacing, clear hierarchy, subtle dividers and 8–12 px corner radii.
- Use generous but purposeful spacing, compact toolbars and consistent controls. Avoid excessive gradients, glow, glass effects, decorative statistics and oversized icons.
- Use text and icons in addition to color for warnings/status. Do not use warning colors as decoration.
- Small purposeful transitions only; honor reduced motion. No autoplay on initial load.
- Create a simple original Argus wordmark. Do not use generated decorative imagery in place of scientific observations.

### Screen structure

1. **Explorer:** small header with Argus, source/workspace selector, search and help; a compact search panel; large central cutout; bottom date timeline; collapsible right inspector.
2. **Analysis:** contextual tabs/drawer for spectrum, brightness history, stack, difference and motion. Maintain the selected source/region when opening tools.
3. **Investigations/reports:** saved drafts and immutable report revisions; clear read versus edit state; evidence, warnings and provenance before sharing/export.
4. **Guided investigations:** concise validated activities using real observations, with a separate labeled simulated training mode if supplied.
5. **Sources/methods:** source status, release labels, attribution, methods, limitations, resource links and required notice.
6. **Embedded view:** compact read-only observation/report view with its own framing policy.

Do not require a marketing landing page before the explorer. First use should show search, example targets and a brief dismissible instruction. Do not load a fake starfield as if it were SPHEREx.

### Viewer behavior

Search accepts object name or explicit RA/Dec. Show coordinate units/reference identity and a bounded FOV width/height in arcminutes. Numeric FOV changes data selection; zoom changes the loaded display. Pan within the loaded boundary; deliberate Load/Recenter requests another patch. Support rectangular/circular selection with a sky footprint and request-size estimate where available.

Show time, wavelength, mission/release, angular scale and orientation. Keep one sky position and zoom through epoch changes. Offer stepping, play/pause, optional loop, speed, A/B blink, synchronized side-by-side/swipe and reset. Distinguish wavelength playback from time playback, and animation speed from actual time gaps.

Evidence Lens opens on source selection. Basic controls remain visible; advanced settings are progressively disclosed. Controls must have tooltips or concise explanations without hiding essential meaning. On mobile, stack/drawer the search and inspector, keeping playback accessible. Keyboard shortcuts must not fire while typing in fields.

Loading states preserve the query, show genuine stages/counts and offer safe cancellation. Distinguish no coverage, insufficient comparable epochs, single frame, partial results, unsupported analysis and upstream outage. Don't label unknown progress with invented percentages.

Implement state ownership, abort stale requests, retain current viewport, bound decoded image memory, release resources, and test high-DPI Canvas pointer transforms. Canvas must have accessible DOM controls and a textual source summary. Survey layers and generated products need clear provenance and legends.

## 5. Architecture and structural plan

Reuse the existing Django scaffold if present. Recommended module responsibilities:

| Module | Ownership |
|---|---|
| `apps/explorer` | Search orchestration, sequences and explorer pages |
| `apps/observations` | Archive adapters, product identity, frames and artifacts |
| `apps/reference` | Object resolution, Gaia DR3, WISE context and supported catalog queries |
| `apps/jobs` | Durable jobs, dispatch intent, quotas, heartbeat, progress and recovery |
| `apps/analysis` | Analysis requests, parameter validation and result records |
| `apps/evidence` | Candidate positions, classifications, notes and checks |
| `apps/reports` | Immutable reports, access grants, exports and independent reviews |
| `science/` | Framework-independent FITS/WCS, response, masking, photometry and image operations |
| `static/src/js/` | viewer, timeline, state, search, layers, analysis, evidence, reports |
| `deploy/` | Containers, Nginx, health checks, production startup and backup/restore |

Use provider adapters such as `observations/providers/spherex.py` and `observations/providers/neossat.py`. Their contracts normalize identity/time/geometry but preserve mission-specific metadata and capabilities. Catalogs do not masquerade as image providers.

Persist normalized requests, immutable observation versions, jobs/attempts, dispatch intent, artifacts/checksums/WCS/units, frame contributors, sequences, candidates/annotations, analysis results, report revisions, read-share grants and reviews. Use constraints and transactions. Product reprocessing is not a new observing epoch.

Web requests validate and return promptly. Cache hits return a sequence reference; new work creates a persistent job and dispatch intent transactionally and returns 202/status URL. Publish after commit and reconcile lost dispatches. Workers retrieve/process/store atomically and update the database. Redis messages carry IDs, not large arrays. Tasks must tolerate redelivery and restarts.

Job states: queued, running, partial, completed, failed, cancel_requested and cancelled. A partial result records usable and excluded observations. Retry transient failures only, with limits/backoff. Cancellation of one viewer must not delete a result needed by another subscriber.

Cache identity includes source/release/product version, region/grid, date/response selection, mask policy, algorithm parameters and software/calibration version. Private access remains separate from deduplicated public scientific artifacts. Pin report evidence or provide a precise retention/reconstruction policy. Never expose filesystem paths.

Use same-origin session authorization and CSRF. Browsing is public; draft edits belong to secure server-side sessions or an implemented account. Explain session-loss behavior. Read links are separate, revocable capabilities; UUIDs alone are not authorization. Provide safe revision conflict handling.

### API contracts

Implement versioned `/api/v1/` routes for resolution, discovery/searches, jobs/status/cancel, sequences/manifests, artifacts, analyses, candidates/annotations, reports/revisions, share creation/revocation, exports and reference catalogs. Freeze request/response schemas before frontend integration. Document exact methods and examples in API_CONTRACTS.md.

Require explicit units, finite coordinates, valid FOV, safe date ranges, supported source/product/algorithm enums and bounded frame/pixel/byte counts. Return normalized selections and applied limits. Use stable error codes, request/job IDs and retryability. Paginate metadata with stable snapshots and cursors. Source capabilities determine which tools are applicable; this is not permission to leave required methods unimplemented.

Manifest fields include schema version, sequence/frame IDs, data mode, source/release, actual time intervals/original time scale, output geometry/WCS, units, artifacts, contributors, wavelength/quality information and warnings. Missing values are null with reasons, not sample defaults.

## 6. Scientific correctness and flaw resolution

Use official archive metadata, documented public interfaces and bounded downloads. Resolve URLs from metadata; do not guess undocumented table columns, files or data-release names. Name resolution returns a reference position, not necessarily a current one. Handle proper motion, coordinate epochs, RA wrapping/poles and explicit hours/degrees. A static source resolver is not a solar-system ephemeris service; add that separately if supported.

Read FITS HDUs by semantic meaning, preserve native arrays/headers and use explicit calibrated units. Separate display stretch from numerical measurements. Align comparable epochs on a fixed celestial grid, preserving footprint/masks. Handle categorical flags separately from floating-point interpolation, and propagate variance with an appropriate method. Test pixel origin, axes, vertical inversion and world/pixel round trips through resize, pan and export. Reprojection alone does not prove accurate alignment; measure residuals where possible.

SPHEREx response varies across a detector. Same detector or nominal channel alone does not establish comparability. Establish a justified local wavelength/response-overlap policy. Use appropriate calibration products for quantitative analysis; visualization lookup metadata alone is not a complete photometric calibration. Represent regional comparability with valid coverage rather than claiming a single source check validates an entire field.

Decode invalid, caution and informational flag bits individually using release definitions. Nonzero flags do not always mean invalid. Preserve raw values, saturation/NaN/coverage state and masking decisions. Background models must not be subtracted twice.

Before stacking, define contributors, weights, time bins, response/coverage and uncertainty assumptions. Account for moving-source smearing. Detector composites must describe their effective response. Before subtraction, address response, registration, photometric scale, background and PSF. Subtract calibrated arrays, not rendered PNG/JPEG values. Report correlated-noise limits and positive/negative residuals honestly.

Photometry uses validated aperture/PSF modeling, local background, solid-angle/unit conversion where relevant, blending checks, corrections and uncertainties. A raw center pixel is not source flux. Spectral points retain dates and bandpasses; never invent channels or imply noncontemporaneous samples are simultaneous. Upper limits need a documented method. On-demand spectra are real queued jobs with caching; do not invent an IRSA extraction API by inspecting a GUI.

Measure motion with spherical geometry or a justified tangent plane, time baseline, RA cosine factor where appropriate and uncertainty. Manual marks may associate different objects. Two epochs do not confirm an orbit, distance or new planet. Follow Mode is explicitly candidate-centered and separate from background-fixed evidence. Candidate suggestions should use explainable conventional detection first, not invented AI confidence.

Gaia DR3 positions require reference-epoch labeling and validated motion propagation where possible. Cross-survey brightness/color differences are not direct variability. A catalog nonmatch is not proof of novelty. NEOSSat tracking geometry and raw calibration require mission-specific checks before applying astronomical measurements.

Audit security/reliability as concrete failure cases: authorization and CSRF, read-share scope/revocation, private exports, SSRF including redirects/private addresses, path traversal, untrusted FITS/resource exhaustion, safe HTML/CSV/filenames, compressed/decompressed size limits, duplicate tasks, lost dispatches, stale UI results, worker failure, full disk, cache eviction, excessive BLAS threads, and persistence/backup restoration. Log testable mitigations and residual limits, not a claim to eliminate every possible flaw.

## 7. Phased execution with acceptance gates

Start by updating existing documents briefly, then build. Avoid spending the task regenerating already adequate prose. Every phase must leave working code, tests, evidence and a resumable progress entry. Continue automatically within this build authorization when the gate passes.

### Phase 0 — Reconcile and prove real data access

Inspect the scaffold, run its foundation checks, review feature dependencies and replace stale foundation-only stopping rules. Verify source documentation and applicable access/data terms. Lock compatible astronomy dependencies. Retrieve one small real SPHEREx cutout; capture IDs, checksum, time, units, WCS, flags and response information. Establish a useful comparable second epoch if available. Check metadata availability for all five challenge targets. Probe Gaia DR3 and NEOSSat access with bounded representative requests and record authentic limitations.

Gate: reproducible actual product retrieval and a documented scientific/adapter contract; blocked providers remain explicitly blocked while independent work continues. Never substitute simulation to pass this gate.

### Phase 1 — Working infrastructure and durable models

Implement PostgreSQL configuration/models/migrations, persistent artifact storage, Celery/Redis, dispatch reconciliation, limits, ownership and status endpoints. Add Linux Compose development services, separate production settings and locked dependencies. Retain the working homepage during transition.

Gate: clean startup, database migrations, real queued processing, idempotency/recovery checks and persistent files. Do not make heavy processing synchronous in HTTP views.

### Phase 2 — Complete core explorer with the minimal product UI

Implement name/coordinate search, presets, custom FOV, discovery, comparable cutouts, previews, shared rendering settings, timeline, playback and A/B blink. Build the polished application shell concurrently with this real workflow. Add pan/zoom, selection, coordinate mapping, orientation/scale, progress/cancel, partial results and robust empty/error states.

Gate: real search → dated frames → inspection works in a browser; stable sky grid, data identity and wavelength warnings are verified. One/no epoch is handled honestly. No fake viewer data outside explicit development fixtures.

### Phase 3 — Evidence, drafts and reports

Implement candidate markings/notes/classes, trails, Evidence Lens, alignment diagnostics where supported, immutable report revisions, ownership, JSON export, read sharing/revocation and URL restoration. Add synchronized side-by-side/swipe and view-state persistence.

Gate: search → mark → inspect → save → reopen → export reproduces evidence. Test access-control failures, editing conflicts, shared cache permissions and pinned artifacts.

### Phase 4 — Validated stacking foundation, then spectral composites

Implement scientific background/quality/response preparation and weighted stacking **before** dependent detector composites. Then implement six detector-group composites, channel/coverage browser, false colour and wavelength playback. Do not schedule SP-05/SP-06 before CH-05; this fixes the earlier milestone dependency conflict.

Gate: known-result stack tests, contribution/response maps, honest gaps and actual channel availability. Linked controls select verified products; no unconditional 102-channel assumptions.

### Phase 5 — Quantitative analysis and motion tools

Implement subtraction with appropriate preparation, residual inspection, calibrated source measurement, spectra, time-series plots, uncertainty/export, apparent-motion measurements, Follow Mode, trial-motion stacking and explainable source suggestions. Ensure the same source/region state flows from viewer to analysis and report.

Gate: numerical reference tests and representative real observations; rejected incompatible requests are explicit. Charts show units, dates, uncertainties and point-to-frame links. All methods have documented limits.

### Phase 6 — Gaia DR3, WISE and NEOSSat workflows

Implement actual Gaia DR3 query/overlay and supported astrometric propagation; WISE reference imagery; layer controls and ambiguous counterpart lookup. Integrate optional Aladin context if retained in the feature contract. Implement NEOSSat/CADC discovery, observation selection, safe download, mission-appropriate processing and dated playback using real observations. Add a verified NEOSSat example, native-frame mode where needed, and source-specific tool availability.

Gate: real DR3 catalog overlay with correct registration and release labels; real WISE context; real traceable NEOSSat sequence or explicitly documented external blocker. Reference resources are all represented on Sources/About, but links alone do not pass dataset-integration acceptance.

### Phase 7 — Complete exports, learning, embedding and maintenance

Implement annotated image/printable/animation/FITS exports, read-only embedding, guided activities, independent review records, incremental source updates, cache cleanup and evidence retention. Provide motion/variability/artifact activities based on verified examples. Implement English accessibility comprehensively; if reviewed translations are part of scope, supply reviewed text and distinguish available languages from future ones.

Gate: exports agree with original evidence and retain dates/units/provenance; embeds cannot mutate; updates do not change immutable reports; keyboard/mobile/reduced-motion workflows pass.

### Phase 8 — Adversarial review, visual polish and performance

Review every control/route and each feature ID. Fix incomplete integration, race conditions, scientific edge cases and stale documentation. Run real desktop/mobile visual inspection, usability tasks, fault injection, authorization tests, duplicate/crash/cancellation scenarios, and bounded local performance measurements. Test third-party outages without sending load to archives.

Gate: all required features have evidence; no placeholder handlers; all known critical defects resolved; measured limits documented. A good screenshot is not a substitute for actual interactions.

### Phase 9 — Release packaging and authorized deployment

Produce tested Linux deployment images/Compose, Nginx/HTTPS configuration, environment example, migrations/static asset build, health/readiness checks, logs, off-server backup/restore and rollback procedures. Rehearse from a clean checkout. Deploy only with available authorization/access, then verify public workflows. If access is absent, finish and test the deployable package locally.

Gate: production-setting checks, migration/backup/restore rehearsal, working persistence, no debug exposure and a truthful release report. State missing external deployment steps precisely.

## 8. Completion, tests and evidence

Maintain `docs/FEATURES.md` using IDs in the appendix plus added resource IDs. Every feature record needs code location, method, dependency, status, executed acceptance check, outcome and remaining limitation. Statuses: planned, in_progress, implemented_unverified, verified, blocked, replaced_with_rationale. No silent deletion or unapproved major scope reduction.

Preserve/update README.md, AGENTS.md, CHANGELOG.md and docs/PRODUCT.md, FEATURES.md, ARCHITECTURE.md, TECH_STACK.md, SCIENCE_AND_DATA.md, API_CONTRACTS.md, DATA_MODEL.md, UX_SPEC.md, IMPLEMENTATION_PLAN.md, DECISIONS.md, FLAW_AUDIT.md, TEST_PLAN.md, TARGET_VALIDATION.md, DEPLOYMENT.md, OPERATIONS.md, SOURCES.md and PROGRESS.md. Add `docs/RESOURCE_INTEGRATION.md` for provider/interface/version/license/real-data evidence and `docs/RELEASE_CHECKLIST.md` for acceptance. The documents must reflect actual implementation rather than permanent foundation-only descriptions.

All five challenge targets must be attempted and documented: Barnard’s Star, Epsilon Indi B, WISE 0855, RW Aurigae, R Draconis. Resolve reference epochs properly; do not assume both Epsilon Indi B components are resolved. WISE 0855 supplied reference coordinates are 08h55m10.831s, −07d14m42.53s; verify epoch before treating them as current. Some targets may legitimately lack useful data, but a complete product needs successful real examples as well as honest failures.

Run focused unit and scientific known-result tests; integration tests with realistic licensed fixtures; PostgreSQL constraints/concurrency; browser end-to-end tasks; mobile/keyboard/reduced-motion checks; and deployment/recovery tests. Synthetic numerical fixtures must be separate from real observational fixtures. Routine CI is offline; real archive checks are opt-in and bounded. Establish science tolerances from method/calibration evidence, never just loosen them to pass a test.

Measure actual cold/cached processing time, peak RAM, CPU, download/cache bytes, queue wait and browser memory. A starting 4-vCPU/16-GB/160–200-GB Linux VPS is only a planning estimate. Start one scientific task at a time; tune concurrency/quotas from measurements. No guaranteed visitor count or instant spectrum claim. Keep expensive operations queued and a bounded preview cache in the browser.

Before claiming full completion, reconcile every required feature, provider integration, visible action and release check. If an external dependency blocks something, keep working on other features and report the blocker, attempted remedy and remaining work; do not call that feature finished. If a session ends, leave exact continuation instructions and verified checkpoints. Do not stop to seek permission for ordinary steps already authorized here.

Final handoff: actual implemented capabilities, feature-evidence summary, real datasets/targets used, commands to run/build/test/deploy, test outcomes, screenshots of the real app, source/license acknowledgements, measured limits, unresolved issues and any deployment access still needed.

## 9. Full retained feature inventory

The 70 IDs below are retained from the agreed product specification. C/N/A express build order and complexity, not a planning-only stopping rule. Words such as “optional” identify a conditional integration choice that must have an explicit documented disposition. They do not permit silent omissions. The baseline full release includes every non-optional behavior; optional features must be implemented or clearly excluded by the agreed contract, never counted as completed merely because a button exists.

### 9.1 Sky Explorer

| ID | Priority | Feature and acceptance expectation |
|---|---|---|
| EX-01 | C | Explicit RA/Dec entry; decimal degrees and sexagesimal with unambiguous units; validate ranges and nonfinite values |
| EX-02 | C | Object-name resolution; show canonical identity when available, resolved coordinates, resolver, and reference-epoch limitations; handle unknown/ambiguous names |
| EX-03 | C | Five target presets: Barnard’s Star, Epsilon Indi B, WISE 0855, RW Aurigae, R Draconis; verified coordinates and provenance |
| EX-04 | C | FOV presets and bounded custom width/height in arcminutes; distinguish square width from radius |
| EX-05 | N | Draw rectangle/circle within the loaded patch; convert selection to celestial coordinates; request a new cutout explicitly |
| EX-06 | N | Estimate observation count and expected transfer/processing work when metadata supports it; label estimates |
| EX-07 | C | Search results with chronological observations, wavelength coverage, quality information, and partial coverage |
| EX-08 | C | Real aligned cutout display, correct orientation and scale, blank/masked uncovered pixels |
| EX-09 | C | Play/pause, next/previous, loop option, playback speed, date labels and frame count |
| EX-10 | C | A/B blink with stable sky position and display settings |
| EX-11 | N | Synchronized side-by-side and swipe comparison, common zoom and viewport |
| EX-12 | C | Zoom/pan within loaded patch; boundaries visible; changing FOV/refetching distinct from display zoom |
| EX-13 | N | Cursor coordinate readout, north/east indicators, angular scale, crosshair, reset view and fullscreen |
| EX-14 | N | Date-range filtering, frame inclusion/exclusion, timeline gaps, and explicit time span of composites |
| EX-15 | C | Distinct loading, resolving, queued, downloading, processing, partial, no-coverage, no-comparable-data, single-epoch and error states |
| EX-16 | C | No large new archive fetch for every pan/wheel event; explicit load/recenter action with stale-request cancellation |

### 9.2 Spectral Lab

| ID | Priority | Feature and acceptance expectation |
|---|---|---|
| SP-01 | C | Position-dependent wavelength and bandwidth readout; comparable-observation selection with documented tolerance |
| SP-02 | N | Nominal 102-channel browser based on verified product/channel definitions; unavailable channels remain absent/disabled with explanation |
| SP-03 | N | Date-by-wavelength coverage matrix linked to viewer selections |
| SP-04 | N | Six detector-range entry points with actual coverage labels |
| SP-05 | A | Six separately constructed detector-group composites with masks, weights, effective response/coverage and time-span provenance |
| SP-06 | A | False-colour composite of selected wavelength ranges with legend, date ranges and explicit infrared mapping |
| SP-07 | A | Wavelength playback clearly distinguished from observation-time playback |
| SP-08 | C | Shared contrast/stretch across compared frames, reset controls; display transformations never alter measured flux |
| SP-09 | A | Click-to-request source spectrum as a background job; extraction method and assumptions recorded |
| SP-10 | A | Flux-versus-wavelength chart with units, uncertainties, gaps, flags, underlying observation links and timestamps |
| SP-11 | A | Epoch-specific spectra and matched-band brightness history where data permit; no invented simultaneous spectrum |
| SP-12 | A | CSV/JSON measurement export and cached analysis results with exact processing versions |

### 9.3 Change Lab

| ID | Priority | Feature and acceptance expectation |
|---|---|---|
| CH-01 | C | Manual source marking per frame; editable notes and classifications: possible motion, brightness change, artifact, unsure |
| CH-02 | N | Position trails and angular separations using celestial geometry |
| CH-03 | A | Apparent-motion fit/estimate with units, time baseline, uncertainty and manual-selection limitations |
| CH-04 | N | Follow Mode centered on selected positions; separate labeled view preserving original fixed-sky comparison |
| CH-05 | A | Quality-aware weighted stacking; choice of time window, contributors, coverage and uncertainty treatment |
| CH-06 | A | Difference image with spatial, spectral, background, photometric and PSF preparation documented |
| CH-07 | A | Positive/negative residual view centered on zero; original A/B observations available beside results |
| CH-08 | A | Trial-motion shift-and-stack with explicit assumed motion, coverage, and validation controls |
| CH-09 | A | Optional source-detection suggestions after baseline validation; report candidate evidence, never an invented discovery probability |

### 9.4 Evidence Lens and reference context

| ID | Priority | Feature and acceptance expectation |
|---|---|---|
| EV-01 | C | Dates, observation IDs, release and original archive links for selected evidence |
| EV-02 | C | Selected-source/region wavelength comparison with readable explanation |
| EV-03 | C | Decoded flag categories and coverage overlay; document masking policy and retain raw bit values |
| EV-04 | N | Measured alignment diagnostic with method and residual; return “not assessed” when absent |
| EV-05 | N | Measurement uncertainty and availability of independent repeat observations |
| EV-06 | C | Processing provenance, warnings, and “comparable / review needed / not assessed” statuses |
| EV-07 | N | WISE reference imagery with survey, wavelength, resolution and epoch labels |
| EV-08 | N | Gaia source catalog overlay with identifiers, reference epoch, and available attributes |
| EV-09 | N | Layer visibility, opacity and legends; source detail popup |
| EV-10 | A | Epoch-propagated catalog positions using available astrometry and explicitly documented approximations |
| EV-11 | A | Possible counterpart list with separation, search radius and ambiguity; absence of a match is not a discovery |
| EV-12 | N | Optional Aladin reference context integrated with the main coordinate selection; main cutout viewer works independently |

### 9.5 Observation Reports and sharing

| ID | Priority | Feature and acceptance expectation |
|---|---|---|
| RP-01 | C | Persist candidate annotations and private investigation drafts with defined ownership |
| RP-02 | C | Immutable report revisions capturing observation IDs, coordinates, times, settings, markers, warnings and provenance |
| RP-03 | C | Shareable read-only report link; explicit sharing action, revocation behavior and documented retention |
| RP-04 | C | Coordinate URL parameters; validated units; restored state cannot bypass request limits |
| RP-05 | N | Full view-state links preserving dates, wavelength selection, FOV and display mode |
| RP-06 | C | JSON report export and original-data links |
| RP-07 | N | Annotated PNG, printable report, and animation export with dates, provenance and real/simulated labels |
| RP-08 | A | Processed FITS export with valid headers/WCS, units, masks and processing history |
| RP-09 | N | Read-only embeddable viewer with an explicit framing policy and no edit secrets in its URL |
| RP-10 | A | Independent review records distinct from the original report; agreement is not scientific confirmation |

### 9.6 Guided learning, accessibility and operations

| ID | Priority | Feature and acceptance expectation |
|---|---|---|
| UX-01 | C | Short guided start, explanations of coordinates/FOV/wavelength/time, no mandatory browsing login |
| UX-02 | N | Validated activities for motion, variability and artifacts; separate labeled simulated training mode if useful |
| UX-03 | C | Responsive layout, keyboard frame stepping, accessible labels, focus, contrast, text alongside colour, reduced motion |
| UX-04 | N | Lightweight previews, lazy frame loading, memory-bounded playback, touch controls and optional reviewed translations |
| OP-01 | C | Configurable release-aware archive adapters, manual refresh, cache time and data-through time |
| OP-02 | N | Scheduled incremental refresh, bounded metadata scans and changed-product handling |
| OP-03 | C | Deduplicate reprocessed copies of the same observation; preserve preferred and superseded versions |
| OP-04 | C | Version-aware cache keys, atomic artifacts, expiry and preservation of evidence referenced by saved reports |
| OP-05 | C | Background processing, progress stages, cancellation, retries, per-user/session limits, timeouts and request quotas |
| OP-06 | C | Logs, health/readiness checks, resource metrics, persistent storage, backups and tested restore |
| OP-07 | C | Source/license acknowledgements, methods page, real limitations and feature-status documentation |

### 9.7 Challenge traceability

New releases map to OP-01–04. The 102 channels and six detector composites map to SP-01–07. Spectra map to SP-09–12. Image addition/subtraction maps to CH-05–08. FOV maps to EX-04–06. Gaia/WISE maps to EV-07–12. Coordinate URLs and embedding map to RP-04–05 and RP-09. Contamination metadata maps to EV-01–06. The selected astronomy tools are specified in Section 3.


## 10. Additional supplied-resource requirements

These are additions to the retained inventory, not substitutes for SPHEREx features.

| ID | Requirement | Acceptance |
|---|---|---|
| RS-01 | Resource/provider registry and capability metadata | Each supplied resource has a role, authoritative URL, access/terms status and real integration or inspiration classification |
| RS-02 | Explicit Gaia DR3 integration | Actual DR3 bounded results, source IDs/epochs, overlay registration and provenance; no DR2 substitution |
| RS-03 | Documented SPHEREx tutorial adaptation | Relevant notebook/version, derived implementation, license/attribution and real archive verification recorded |
| RS-04 | WiseView-inspired comparison experience | Credit inspiration; working blink UX; no copied assets/code without permission or invented API dependency |
| RS-05 | CSA/CADC NEOSSat adapter | Actual supported discovery/download interface, pagination/limits, release/product IDs and tests |
| RS-06 | NEOSSat observation workspace | Real dated sequence, verified example, mission-specific calibration/geometry, source labels and honest unsupported states |
| RS-07 | NEOSSat tutorial/dataset provenance | Tutorial commit/terms, original dataset/file identity/checksum and source acknowledgements captured |
| RS-08 | Agency notice and resource-specific terms | Supplied NASA notice, mission acknowledgements and relevant data-use terms represented accurately; no endorsement claims |

## Final execution instruction

Begin from the existing repository now. Reconcile outdated planning-only instructions, verify the foundation, make a concise dependency-aware execution plan, and proceed through the build phases with real code and tests. Deliver integrated working behavior and preserve scientific honesty. Do not stop at documentation, scaffolding or a visual prototype. Keep the full feature and resource ledger current until delivery or an explicitly documented external blocker.
