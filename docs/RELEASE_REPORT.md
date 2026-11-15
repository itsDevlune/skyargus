# Development handoff — 2026-11-15

Argus is an integrated, working local Django application. **The full requested release is not complete.** All 70 retained feature IDs plus 8 resource IDs remain in [FEATURES.md](FEATURES.md); unfinished requirements have not been removed or approved out of scope.

Latest offline verification on 2026-11-15: **205 pytest passed** (3 Astropy warnings); Playwright **18 passed, 10 skipped** because fixed real-cache sequence IDs were absent from the current local database; changed-file Ruff, JavaScript syntax checks and Django system check passed. Full Ruff still reports three existing findings in the tutorial evidence script. `.venv313` is Python 3.12.5, not the requested 3.13.15. No archive calls, manual browser review, Linux/PostgreSQL/Celery, or production checks were performed in this verification.

Implemented behavior includes explicit coordinate/name searches, bounded FOV/release/detector/date selection, durable background jobs and file cache, genuine SPHEREx dated cutouts, north-up fixed-grid display, playback/blink/side/swipe, pan/zoom/reset, coordinate marking and notes, Evidence Lens, immutable report snapshots and revision chains, session ownership, read capabilities and revocation, JSON/PNG/GIF/print exports, native/display FITS access, manual apparent-motion jobs, Gaia DR3 queries/overlay and separate NEOSSat raw native-detector playback.

Real evidence:

- Eight SPHEREx DR1 detector-3 exposures near explicit ICRS 269.452075°, +4.693391°, 6×6 arcmin; dates Aug 15–18, 2025. Reference coordinates are not claimed to be Barnard's Star's propagated 2025 position.
- All five challenge target names resolved and returned bounded exposure metadata. Useful matched-response photometry remains unverified.
- Actual `gaiadr3.gaia_source` results at J2016.0; proper motion is returned but not propagated.
- Four CADC NEOSSat raw optical FITS exposures, October 13, 2019, using actual DATASEC and no invented sky registration/calibration.
- Source IDs, original links, checksums, units, dates and geometry: [real manifests](evidence/real-manifests.json). Tutorial commits/licenses/methods: [resource evidence](RESOURCE_INTEGRATION.md).

Earlier release checkpoint: **29 pytest tests** and **3 formal Playwright tests**, Django migrations/check and migration drift check, clean Windows hash-locked installation/dependency compatibility, Ruff, compiled Tailwind build and npm audit (zero reported vulnerabilities). Additional real-data browser scripts verified marking, queued motion fit, report save/reopen, exported PNG/GIF (HTTP 200), dated playback/comparison, high-DPI coordinate roundtrip, no JavaScript errors and zero archive-search requests during pan/zoom. Production Django check reported W021 only: HSTS preload is intentionally not committed without a production domain.

Measured bounded local work: eight repeated passes over one real fixture took 0.273 s wall/0.266 s CPU, peak process working set 154 MB; cached durable job returned in 0.039 s. These are not cold archive throughput, browser decoded-memory or visitor-capacity measurements. Details: [performance evidence](evidence/performance.json), [Canvas/OpenSeadragon startup comparison](evidence/viewer-benchmark.json).

Screenshots: [real explorer](evidence/real-explorer.png), [comparison](evidence/real-comparison.png), [read-only report](evidence/real-report.png), [NEOSSat native view](evidence/neossat-native.png), [mobile](evidence/explorer-mobile.png), [light theme](evidence/explorer-light.png). The empty explorer screenshots intentionally contain no sky image; real-data screenshots are separate.

Run/build/test/deploy commands are in [DEPLOYMENT.md](DEPLOYMENT.md) and [TEST_PLAN.md](TEST_PLAN.md). The web application and local database worker were left running at **http://127.0.0.1:8000/**. SQLite/data files retain downloaded observations and report evidence, and are gitignored. A pinned real FITS test fixture is committed as project content; synthetic numerical fixtures remain separate.

Required remaining work includes calibrated spectral response/flag/PSF/background preparation; weighted stacking integration and uncertainty propagation; six detector composites/false color/channel coverage; calibrated differences/photometry/spectra/brightness charts; Follow Mode/trial stacks; WISE imagery; Gaia propagation/counterparts; guided activities; complete accessible source interaction; source-version refresh/retention and operational fault/concurrency testing. Some export/view-state/review/embedding acceptance also remains open. These are unfinished engineering/science tasks, not falsely labeled external blockers.

External constraints: two bounded WISE metadata requests timed out; the CSA dataset page timed out and WiseView returned a gateway error. CADC supplied a successful alternative for NEOSSat. Docker is absent, so Linux/PostgreSQL/Celery/Redis, production image startup and backup/restore have not been executed. No authorized production host, domain/TLS material or deployment credentials were supplied. Compose/Gunicorn/Nginx/HTTPS configuration and backup procedure are prepared, **not validated production deployment**. No external publication occurred.

Continue from [PROGRESS.md](PROGRESS.md), [FLAW_AUDIT.md](FLAW_AUDIT.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) and the full feature ledger. Existing build authorization remains active; routine implementation does not require another permission request.
