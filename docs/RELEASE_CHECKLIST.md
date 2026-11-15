# Release acceptance checklist
- [x] Real Django app, migrations, isolated environment and short web requests
- [x] Actual SPHEREx DR1 cutout retrieval and dated browser workflow
- [x] All five target resolution/discovery attempts recorded
- [x] Real Gaia DR3 query and separate real NEOSSat native raw sequence
- [x] Session ownership, CSRF, report snapshots, read sharing/revocation tests
- [x] Scientific numerical and real-file fixture tests (29 passed)
- [x] Offline browser shell tests (3 passed), desktop/mobile screenshots
- [ ] Every feature/resource acceptance gate (FEATURES.md contains unfinished requirements)
- [ ] Calibrated response/flags/PSF, scientific stacks/differences/spectra/composites
- [ ] WISE imagery, Gaia propagation/counterparts, guides and optional dispositions
- [ ] Worker crash/retry/duplicate/cancel, durable constraints and quota fault tests
- [ ] Full export/embedding/review workflows verified
- [ ] Linux clean build, PostgreSQL/Celery/Redis runtime and production HTTPS
- [ ] Measured peak RAM/CPU/browser memory, off-server backup and restore rehearsal
- [ ] Authorized external deployment and public workflow checks

Do not label this a complete 70-feature release while unchecked items remain.
