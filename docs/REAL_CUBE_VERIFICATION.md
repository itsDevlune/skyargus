# Real 102-channel DR1 cube acceptance

Verified 15 November 2026 against a genuine downloaded IRSA product, not a controlled response.

## Data and integrity

- Field: ICRS RA269.452075°, Dec4.693391°.
- Actual covering tile: HPX order5 tile7945.
- Source: https://irsa.ipac.caltech.edu/ibe/data/spherex/dr1/hips5_cube/hips_20261026/Norder5/Dir0/Npix7945_cube.fits
- Complete size:320909760 bytes.
- SHA256:00e6e83df65d7e85eabb7029fc99d924e9e8c631037572bc2e7453935f9cc5b7.
- Stored cube dataset:cc0ecc9e-4040-49a3-aab3-affc8a14b6fd.
- IMAGE shape:102×512×512. All six HDUs retained, including final WCS-WAVE.
- 100 available channels; one-based channels51 and52 blank in this actual product.
- Wavelength, bandwidth, detector and subchannel come from SPECTRAL_CHANNELS, not an assumed linear wavelength grid.

The earlier range probe of tile6270 established archive format, not the actual tile for this test field. Earlier timeout checkpoints are superseded by this successful complete retrieval.

## Checks performed

`scripts/verify-real-cube.py` compared all102 central-pixel samples to original IMAGE values and verified hits, flags, spectral-table wavelengths and spatial coverage alpha/orientation. It also checked extraction at the requested sky position against original array values and verifies the original artifact hash. Result arrays and provenance are in evidence/real-cube/metadata.json, pixel-spectrum.json and source-spectrum.json.

`scripts/verify-cube-browser.cjs` used real backend routes and genuine cached data. It loaded the cube through the UI, checked102 controls, moved the slider to63, loaded its512px plane, extracted at both pixel and marked/field position, verified102 table rows and the uncertainty warning, downloaded JSON and matched its original FITS hash. Coverage mode switched successfully; no page errors were recorded. See browser-result.json and browser-spectrum.json.

Screenshots: [channel controls](evidence/real-cube/channels-browser.png), [actual cube image](evidence/real-cube/image-browser.png), [actual spectrum](evidence/real-cube/spectrum-browser.png). Images and graphs were visually inspected. Expand panel provides enough space for the coverage grid and spectrum.

Offline checks:242 Python tests,33 Playwright tests, application Ruff. Two added transfer regressions verify resume and corruption detection. Further five tests validate sky-coordinate inputs. Browser verification helpers are opt-in because they create a private cube job and use local genuine cache.

## Transfer behavior

Each job has a210-second download budget and at most three simultaneous1MiB range requests. Complete chunks are stored atomically under data/cube-transfers with SHA256 sidecars. Retry verifies cached bytes before reuse; damaged chunks are fetched again. Partial/incomplete responses are never accepted. Header probes require the actual six-HDU layout. The first test needed successive bounded attempts on this slow connection; the finished dataset is reused without re-downloading the cube.

An old worker initially misclassified a cube job. The stale worker was stopped and restarted. Unknown kinds now fail explicitly instead of entering sequence processing. Restart both Django and workjobs when installing new job types.

## Scientific limits

The cube is a multi-date mosaic, not an exposure-time sequence. Viewer orientation is native HPX. Spectrum values sample one nearest mosaic pixel in MJy/sr, not aperture-integrated point-source flux. Coordinate sampling uses the complete cube WCS. Finite IMAGE and NHITS>0 define displayed coverage; raw flags are retained but not decoded into a validated photometric quality selection. There is no supplied propagated variance in this product, so uncertainty is explicitly unavailable. Molecular classification and calibrated spectral fitting remain unimplemented.
