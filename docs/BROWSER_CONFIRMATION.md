# Browser confirmation — 15 November 2026

## Follow-up recheck

Fixed asynchronous cube state issues: playback scheduling now fences obsolete timer generations when speed/pause changes during image loading; delayed image completion cannot restart hidden blink or clamp a hidden viewport; stale spectrum responses from a previous cube are discarded; failed old image promises cannot evict a newer cache entry. Reopening a visible blink panel resumes one timer. Added a delayed-image panel-close/reopen regression; it passed with the genuine cube. Genuine cached browser workflow passed again. Full recheck:34 browser tests,246 Python tests and application Ruff passed; expanded focused comparison test passed after the final hidden-panel guard.

Ran actual Chromium browser interactions against http://127.0.0.1:8000 using genuine cached SPHEREx observations/cube. These are automated browser checks, not a claim of physical-device touch testing.

## 102-channel viewer

| Control / workflow | Observed outcome |
| --- | --- |
| A/B dropdowns |102 options each; selections update labels and image requests |
| Blink |Alternates visible A/B phase |
| Side by side |Both real planes render with equal dimensions and square aspect |
| Swipe |Split slider changes display boundary |
| Pan |Measured40px horizontal/20px vertical movement; no spectrum request |
| Panel dismissal/reopening |Viewport retained; playback stopped |
| Spectrum selection |Separate tool selects mapped pixel; one spectrum request;102 result rows |
| Wavelength play/pause |A advances; pause changes pressed state and stops playback |
| Previous/next/loop |End stays at102 without loop; wraps102→1 with loop; previous wraps1→102 |
| Interval |400ms setting selectable; images wait for readiness rather than claiming fixed video FPS |
| Native pixels |Canvas draw width512 CSS pixels for512-pixel tile |
| Fit |Returns full tile inside viewer |
| Contrast/reset |Canvas contrast changes to1.6 then control resets to1 |
| Interpolation |Smooth enables canvas image smoothing |
| Fullscreen |Entry passed. Found Escape/workbench conflict, fixed explicit fullscreen handling; both Escape and in-view exit button now pass |

All34 browser regressions passed. Expanded focused cube regression passed again after adding explicit exit-button assertions. Real cached cube UI verification passed with JSON export/hash validation and no page errors.

## Other workflows checked

`node scripts/ui-roundtrip.cjs` passed: genuine cached field, saved manual notes, report contents, continuation restoring frame/contrast/selected position, PNG/GIF downloads, PDF generation, read-only share in separate context and404 after revocation. It creates private verification records; prior user records are preserved.

The full suite also checks exposure playback, keyboard scope, comparison geometry, pending request state, coordinate/preset handling, partial errors, native NEOSSat restrictions, Gaia/WISE overlay presentation and source/method acknowledgements. Some external-service paths use controlled responses; this run does not certify current live ESA/IRSA connectivity or scientific calibration. Existing scientific warnings remain applicable.

Evidence: [genuine channel comparison](evidence/real-cube/comparison-browser.png), [cube spectrum](evidence/real-cube/spectrum-browser.png), [report/share workflow](evidence/ui-roundtrip/results.json).
