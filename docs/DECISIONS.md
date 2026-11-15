# Material decisions
2026-11-15: Repository was empty except .git (unborn main). There was no Django scaffold or stale document to preserve. Built one Django project rather than restarting a previous project.

Use one compact core app plus framework-independent science modules while contracts stabilize. Alternative seven empty Django apps would add boilerplate without boundaries. No microservices/React/AI dependency introduced.

Use local database polling in a separate process on Windows. Celery remains the production Linux worker via Redis; web requests do not run cutout jobs synchronously. Tradeoff: local SQLite concurrency is not proof of PostgreSQL behavior.

Use CDS-recommended IDIA Sesame mirror because primary SIMBAD returned 404 and CDS reports degraded Strasbourg services. Resolver returns reference coordinates/proper-motion attributes and warns catalog epochs are not supplied/propagated. No static preset is claimed as a current ephemeris.

Use separate native raw-detector NEOSSat display because validated celestial registration/calibration is absent. Science DATASEC crop is justified by FITS header, original raw file retained. Optical data never impersonate SPHEREx infrared images.

Canvas was implemented provisionally before the requested OpenSeadragon evaluation. The subsequent five-sample real-preview benchmark (evidence/viewer-benchmark.json) measured Canvas image-open times 51.6/1.2/0.5/1.6/0.4 ms, versus OpenSeadragon 257.3/15.9/9.9/8.8/9.8 ms. This limited startup test does not compare large pyramids or full playback performance. Retain one primary Canvas viewer for the current small pre-reprojected cutouts (58×58 pixels at 6 arcmin), exact TAN mapping and annotations; reevaluate OpenSeadragon if larger products require tiling. No competing viewer is shipped in the UI.

Firefly client evaluation: Caltech/IPAC tutorials use `firefly-client` to launch standalone browser sessions against remote IRSA viewer servers (e.g. `https://irsa.ipac.caltech.edu/irsaviewer`). In an embedded web application, calling Firefly Python client opens external browser windows or relies on unauthenticated cross-origin iframe embedding, which violates framing policies and fails offline CI. We retain the native Canvas renderer with exact WCS mapping and implement the underlying tutorial FITS/WCS/aperture photometry and spectral extraction directly.

Scientific analyses (spectrum, difference, epoch stacking, composite): Derived from official Caltech/IPAC SPHEREx tutorials (spherex_cutouts.md, spherex_mosaic.md, and spherex_source_discovery_tool_demo.md / aperture_photometry.py by Zafar Rustamkulov). Quick-look aperture extraction uses un-reprojected native cutouts with local background subtraction, WCS-WAVE lookup with SIP disabled, local pixel solid angle flux conversion, MSKN quality flag masking, and variance propagation. Differences require passband compatibility checks and zero-centered stretch. Stacks apply inverse-variance weighting on the common reprojected celestial grid. RGB composites map 3 distinct wavelength bands to channels with disclosed stretches.

No quantitative spectra/differences inferred from visualization lookup tables or PNGs. Those features remain incomplete until calibrated response, uncertainty and PSF/background handling pass tests.
