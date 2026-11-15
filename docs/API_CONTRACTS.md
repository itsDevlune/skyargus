# API contracts, schema version 1
JSON endpoints are same origin. POST/PATCH/DELETE require Django CSRF and a session cookie. Scientific cache manifests/artifacts are public; jobs, annotations, reports and exports require their owning session. Unowned identifiers return 404. Request IDs appear in X-Request-ID. Error envelope: {"error":{"code":"invalid_request","message":"...","retryable":false},"request_id":"..."}. Codes include invalid_request, quota_exceeded, queue_full, resolver_unavailable, revision_conflict, upstream_or_processing_error. Some Django 404/CSRF errors are HTML; consistent JSON middleware remains required.

| Route | Methods | Contract |
|---|---|---|
| /api/v1/resolve | POST | {name}; identity, ra, dec, unit, resolver, reference, proper-motion attributes and epoch warning |
| /api/v1/searches | POST | {ra,dec,unit:"deg" or "hourangle",width:6,height:6,source:"spherex" or "neossat",release:"dr1" or "qr3",detector:1,start:null,end:null}; 202 job/status_url/normalized selection or 200 cached sequence |
| /api/v1/jobs/UUID | GET, POST | Owner only; state, stage, result, error; POST {action:"cancel"} |
| /api/v1/sequences/UUID | GET | schema_version, selection, frames, excluded, discovery, geometry/WCS, units, warnings, metrics |
| /api/v1/artifacts/UUID | GET | Bytes with SHA-256 ETag; immutable public scientific artifact; no filesystem paths |
| /api/v1/catalogs/gaia | POST | Same bounded region; 202 Gaia DR3 query job |
| /api/v1/analyses | POST | {method:"motion",sequence,position_error_arcsec}, {method:"spectrum",sequence,ra,dec,aperture_radius_pix}, {method:"difference",sequence,frame_a,frame_b}, {method:"stack",sequence,frames:[indices]}, or {method:"composite",sequence,red,green,blue}; indices must be distinct in-range JSON integers. Difference/stack results report nominal display-band overlap separately from calibrated response status; missing response calibration is `not_assessed`. |
| /api/v1/candidates | GET, POST | GET ?sequence=UUID lists private marks; POST {sequence,frame,ra,dec,classification,note} |
| /api/v1/candidates/UUID | PATCH, DELETE | PATCH same fields + revision; 409 on revision conflict |
| /api/v1/reports | GET, POST | List private reports; POST {sequence,title,settings}; creates a new immutable snapshot |
| /api/v1/reports/UUID | GET | Owner-only full immutable JSON |
| /api/v1/reports/UUID/shares | POST, DELETE | Explicit creation returns read URL/embed URL; DELETE revokes all grants for that report |
| /api/v1/reports/UUID/exports/png or gif | GET | Owner-only PNG of settings.index with frame-matching annotations, or dated full-sequence GIF |
| /api/v1/reports/UUID/reviews | GET, POST | Owner or valid ?share=token; {text}; separate review records, session independence is not verified identity |
| /reports/UUID | GET | Owner-only readable report; ?format=json exports snapshot |
| /shared/TOKEN | GET | Revocable read-only report, ?format=json |
| /embed/TOKEN | GET | Read-only, same-origin framing only, no edit token |
| /health/ | GET | DB connectivity and queued count |

Example: curl -c cookies.txt http://127.0.0.1:8000/ first obtains a CSRF cookie; supply it in X-CSRFToken for POST with the same cookie jar. RA hourangle requires explicit unit; numeric FOV is full width/height in arcminutes. No implicit archive request on pan/wheel. Lists are capped; stable cursor pagination is unfinished. Date endpoints currently use day-start boundaries, so an end date is not inclusive of the whole end day; inclusive date handling remains required.

Report creation also accepts optional parent:UUID. The parent must belong to the session and be the latest revision; stale parents return revision_conflict/409. Responses contain revision, parent and investigation identifiers. Private readable reports offer Continue as a new revision. Embeds use a standalone script-free template and CSP script-src none; they cannot issue edits from their UI.

## Geometry diagnostics
Sequence GET adds read-time `inspection.requested`, WCS-derived `inspection.output`, actual loaded-frame `inspection.time` and request/grid consistency. This does not rewrite pinned reports. New frames include archive returned footprint and finite-data valid coverage/bounds. Native detector sequences do not assert celestial footprints. New discovery uses temporal-spread-v1 within a 100-row sample; sampled/selected baselines and truncation caution are explicit.
