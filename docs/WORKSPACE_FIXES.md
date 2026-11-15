# Workspace and audit fixes — 2026-11-15

The previous workspace used tiny labels, a short image stage and a responsive breakpoint that moved evidence out of view. Scientific thumbnails were shown as a small square inside a large empty canvas. Provider exception strings, including full URLs, overwhelmed partial-result observation logs.

Changes:

- Compact search heading, readable 12–14 px controls and labels, larger image stage and near-full-height fit of the original image. Evidence stays in the right column on desktop; mobile still stacks without horizontal overflow.
- Actual image dimensions are labeled. A 6×6 arcminute SPHEREx cutout at 6.2 arcsec/pixel has roughly 58×58 data pixels: enlargement cannot create missing detail. No artificial sharpening or fake sky imagery was introduced.
- Partial results show usable/unavailable counts, a concise explanation, expandable observation details and a **Retry unavailable observations** action. Old stored errors are formatted safely too; new worker errors use stable short codes/messages. Usable downloads are reused, and retry creates a new immutable sequence so saved reports do not change.
- Side-by-side images preserve aspect ratio. B dropdown, contrast, pan and zoom restore consistently from copied view links. Cached sequence ID is included in the view link.
- Native NEOSSat cursor shows detector pixels rather than a false outside-boundary message. It still makes no celestial-registration claim.
- Sexagesimal 24h input and fractional detector values are rejected; malformed UUID payloads return 400; celestial marks outside the loaded field are rejected.
- End dates include the whole selected UTC day. Dated requests include a new cache-policy identity; old report evidence is unchanged.
- Quality flags/long processing details are progressively disclosed. Essential source/date/units/coverage and comparison cautions remain visible. Bandwidth is labeled as bandwidth, not as a measurement uncertainty.
- Loaded fields no longer retain a misleading unrelated object name from the search box.

Verification: **42 Python tests passed**, **5 Playwright tests passed**, Ruff passed; the additional API audit now passes **12/12**. Desktop/mobile visual inspection and scripts/check-workspace-fixes.cjs confirm readability, partial-result formatting/retry request, native coordinates and no JS errors. Browser retry request wiring was tested with a controlled response; the backend retry job contract and preservation of the previous manifest were tested offline. This is not a claim that IRSA's HTTP 503s were repaired.

Screenshots: [desktop](evidence/workspace-fixes/desktop.png), [comparison](evidence/workspace-fixes/comparison.png), [partial results](evidence/workspace-fixes/partial.png), [mobile](evidence/workspace-fixes/mobile.png).

IRSA may still return 503 or time out; Argus retains the usable frames and offers a bounded retry. Gaia upstream connectivity, calibrated spectra/composites, production/Linux verification and the other unfinished science features remain outside these fixes. Historical audit findings are retained; affected feature records must be read with this update.
