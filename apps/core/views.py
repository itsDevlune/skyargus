import hashlib
import json
import secrets
import uuid
from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from science.coordinates import region
from science.geometry import inspect_manifest

from .models import Artifact, Candidate, Dispatch, Job, Report, Review, Sequence, Share
from .providers import resolve
from .tasks import cache_key, publish


def owner(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def api(methods):
    def decorate(func):
        @wraps(func)
        def wrapped(request, *args, **kwargs):
            request.request_id = uuid.uuid4().hex
            if request.method not in methods:
                return JsonResponse(
                    {"error": {"code": "method_not_allowed", "message": "Use " + ", ".join(methods)}}, status=405
                )
            try:
                result = func(request, *args, **kwargs)
                result["X-Request-ID"] = request.request_id
                return result
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                return JsonResponse(
                    {
                        "error": {"code": "invalid_request", "message": str(exc), "retryable": False},
                        "request_id": request.request_id,
                    },
                    status=400,
                )

        return wrapped

    return decorate


def body(request):
    data = json.loads(request.body or "{}")
    if not isinstance(data, dict):
        raise ValueError("JSON object required")
    for key in ["sequence", "parent", "id"]:
        if key not in data:
            continue
        val = data[key]
        if val is None:
            continue
        if key == "id":
            continue
        try:
            uuid.UUID(str(val))
        except (TypeError, ValueError):
            raise ValueError(f"Invalid UUID format for {key}")
    return data


@ensure_csrf_cookie
def explorer(request):
    return render(request, "explorer.html")


def sources(request):
    return render(request, "sources.html")


@api(["POST"])
def resolution(request):
    name = str(body(request).get("name", "")).strip()
    try:
        return JsonResponse(resolve(name))
    except ValueError:
        raise
    except Exception:
        return JsonResponse(
            {
                "error": {
                    "code": "resolver_unavailable",
                    "message": "Name resolver unavailable. Try explicit RA/Dec.",
                    "retryable": True,
                }
            },
            status=502,
        )


@api(["POST"])
def searches(request):
    payload = body(request)
    s = region(payload)
    if payload.get("retry_sequence"):
        previous = get_object_or_404(Sequence, pk=payload["retry_sequence"])
        if not previous.manifest.get("excluded"):
            raise ValueError("This sequence has no excluded observations to retry")
        # New immutable result identity; old reports continue to pin their evidence.
        s = {**previous.manifest["selection"], "retry_of": str(previous.id)}
    return enqueue(request, s, "sequence")


def enqueue(request, s, kind):
    who = owner(request)
    if kind == "sequence":
        cached = Sequence.objects.filter(cache_key=cache_key(s)).first()
        if cached:
            return JsonResponse({"sequence": str(cached.id), "cached": True})
    active_limit = settings.ARGUS_SESSION_ACTIVE_JOBS
    hourly_limit = settings.ARGUS_SESSION_JOBS_PER_HOUR
    if (
        active_limit
        and Job.objects.filter(owner=who, state__in=["queued", "running", "cancel_requested"]).count() >= active_limit
        or hourly_limit
        and Job.objects.filter(owner=who, created__gt=timezone.now() - timedelta(hours=1)).count() >= hourly_limit
    ):
        return JsonResponse(
            {
                "error": {
                    "code": "quota_exceeded",
                    "message": "A configured local job limit was reached. Cached observations remain available.",
                    "retryable": True,
                }
            },
            status=429,
        )
    if (
        settings.ARGUS_QUEUE_LIMIT
        and Job.objects.filter(state__in=["queued", "running"]).count() >= settings.ARGUS_QUEUE_LIMIT
    ):
        return JsonResponse(
            {"error": {"code": "queue_full", "message": "Queue is full; try later", "retryable": True}}, status=429
        )
    with transaction.atomic():
        job = Job.objects.create(owner=who, selection=s, kind=kind)
        Dispatch.objects.create(job=job)
        transaction.on_commit(lambda: publish(job.id))
    return JsonResponse({"job": str(job.id), "status_url": f"/api/v1/jobs/{job.id}", "selection": s}, status=202)


@api(["GET", "POST"])
def jobs(request, pk):
    job = get_object_or_404(Job, pk=pk, owner=owner(request))
    if request.method == "POST":
        if body(request).get("action") != "cancel":
            raise ValueError("action must be cancel")
        if job.state == "queued":
            job.state = "cancelled"
        elif job.state == "running":
            job.state = "cancel_requested"
        job.save(update_fields=["state", "updated"])
    return JsonResponse(
        {
            "id": str(job.id),
            "state": job.state,
            "stage": job.stage,
            "result": job.result,
            "error": job.error,
            "created": job.created.isoformat(),
            "updated": job.updated.isoformat(),
        }
    )


@api(["GET"])
def sequences(request, pk):
    return JsonResponse(inspect_manifest(get_object_or_404(Sequence, pk=pk).manifest))


@require_GET
def artifacts(request, pk):
    a = get_object_or_404(Artifact, pk=pk)
    path = settings.DATA_ROOT / a.filename
    if not path.is_file():
        raise Http404
    response = FileResponse(path.open("rb"), content_type=a.media_type)
    response["ETag"] = '"' + a.sha256 + '"'
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    if a.media_type == "application/fits":
        response["Content-Disposition"] = 'attachment; filename="argus-' + str(a.id) + '.fits"'
    return response


@api(["POST"])
def catalogs(request):
    return enqueue(request, region(body(request)), "gaia")


@api(["POST"])
def wise_catalog(request):
    return enqueue(request, region(body(request)), "wise")


@api(["POST"])
def analyses(request):
    data = body(request)
    method = data.get("method")
    if method not in ("motion", "spectrum", "difference", "stack", "composite"):
        raise ValueError("Supported analysis methods: motion, spectrum, difference, stack, composite.")
    seq = get_object_or_404(Sequence, pk=data.get("sequence"))
    if seq.manifest["geometry"].get("mode") == "native":
        raise ValueError(
            "Scientific analysis requires validated sky coordinates; native detector displacements are unsuitable"
        )

    if method == "motion":
        marks = Candidate.objects.filter(owner=owner(request), sequence=seq).order_by("updated")[:200]
        points = [{**c.data, "date": seq.manifest["frames"][c.data["frame"]]["date"]} for c in marks]
        error = float(data.get("position_error_arcsec", 3.1))
        from science.motion import fit_motion

        fit_motion(points, error)  # Bounded preflight before dispatch; no archive access.
        return enqueue(
            request,
            {
                "sequence": str(seq.id),
                "points": points,
                "position_error_arcsec": error,
                "processing": "manual-motion-v1",
            },
            "motion",
        )

    if method == "spectrum":
        ra = float(data["ra"])
        dec = float(data["dec"])
        ap_rad = float(data.get("aperture_radius_pix", 3.0))
        return enqueue(
            request,
            {
                "sequence": str(seq.id),
                "ra": ra,
                "dec": dec,
                "aperture_radius_pix": ap_rad,
                "processing": "quicklook-spectrum-v1",
            },
            "spectrum",
        )

    if method == "difference":
        from science.analysis import validate_frame_index

        frame_count = len(seq.manifest.get("frames", []))
        fa = validate_frame_index(data.get("frame_a"), frame_count, "frame_a")
        fb = validate_frame_index(data.get("frame_b"), frame_count, "frame_b")
        if fa == fb:
            raise ValueError("frame_a and frame_b must refer to different observations")
        return enqueue(
            request,
            {"sequence": str(seq.id), "frame_a": fa, "frame_b": fb, "processing": "difference-v1"},
            "difference",
        )

    if method == "stack":
        from science.analysis import validate_frame_indices

        if "frames" not in data:
            frames = list(range(len(seq.manifest.get("frames", []))))
        else:
            frames = validate_frame_indices(data["frames"], len(seq.manifest.get("frames", [])))
        return enqueue(
            request,
            {"sequence": str(seq.id), "frames": frames, "processing": "epoch-stack-v1"},
            "stack",
        )

    if method == "composite":
        from science.analysis import validate_frame_index

        frame_count = len(seq.manifest.get("frames", []))
        red = validate_frame_index(data.get("red"), frame_count, "red")
        green = validate_frame_index(data.get("green"), frame_count, "green")
        blue = validate_frame_index(data.get("blue"), frame_count, "blue")
        if len({red, green, blue}) != 3:
            raise ValueError("RGB channels must refer to three different observations")
        return enqueue(
            request,
            {"sequence": str(seq.id), "red": red, "green": green, "blue": blue, "processing": "composite-v1"},
            "composite",
        )


@api(["GET", "POST", "PATCH", "DELETE"])
def candidates(request, pk=None):
    who = owner(request)
    if request.method == "GET":
        items = Candidate.objects.filter(owner=who, sequence_id=request.GET.get("sequence")).order_by("updated")[:200]
        return JsonResponse({"candidates": [{"id": str(c.id), "revision": c.revision, **c.data} for c in items]})
    data = body(request)
    if request.method == "DELETE":
        get_object_or_404(Candidate, pk=pk, owner=who).delete()
        return JsonResponse({"deleted": True})
    seq = get_object_or_404(Sequence, pk=data.get("sequence"))
    frame = int(data["frame"])
    if not 0 <= frame < len(seq.manifest["frames"]):
        raise ValueError("Invalid frame")
    c = region({"ra": data["ra"], "dec": data["dec"]})
    geometry = seq.manifest.get("geometry")
    if geometry:
        if geometry.get("mode") == "native":
            raise ValueError("Celestial annotations require a validated sky grid")
        import math

        from astropy.io import fits
        from astropy.wcs import WCS

        wcs = WCS(fits.Header.fromstring(geometry["wcs"]))
        x, y = wcs.world_to_pixel_values(c["ra"], c["dec"])
        if not all(math.isfinite(v) for v in (x, y)) or not (
            -0.5 <= x < geometry["width"] - 0.5 and -0.5 <= y < geometry["height"] - 0.5
        ):
            raise ValueError("Annotation is outside the loaded field")
    classification = data.get("classification", "unsure")
    if classification not in ("possible motion", "brightness change", "artifact", "unsure"):
        raise ValueError("Invalid classification")
    note = str(data.get("note", ""))
    if len(note) > 4000:
        raise ValueError("Note exceeds 4000 characters")
    normalized = {"frame": frame, "ra": c["ra"], "dec": c["dec"], "classification": classification, "note": note}
    if pk:
        with transaction.atomic():
            obj = get_object_or_404(Candidate.objects.select_for_update(), pk=pk, owner=who)
            if obj.revision != data.get("revision"):
                return JsonResponse(
                    {"error": {"code": "revision_conflict", "message": "Reload the current annotation before editing"}},
                    status=409,
                )
            if obj.sequence_id != seq.id:
                raise ValueError("Cannot move annotation to another sequence")
            obj.data, obj.revision = normalized, obj.revision + 1
            obj.save()
    else:
        obj = Candidate.objects.create(owner=who, sequence=seq, data=normalized)
    return JsonResponse({"id": str(obj.id), "revision": obj.revision, **obj.data}, status=201 if not pk else 200)


def report_data(report):
    return {
        "id": str(report.id),
        "revision": report.revision,
        "parent": str(report.parent_id) if report.parent_id else None,
        "investigation": str(report.root_id or report.id),
        "created": report.created.isoformat(),
        "immutable": True,
        **report.snapshot,
    }


@api(["GET", "POST"])
def reports(request):
    who = owner(request)
    if request.method == "GET":
        return JsonResponse(
            {
                "reports": [
                    {
                        "id": str(r.id),
                        "title": r.snapshot["title"],
                        "revision": r.revision,
                        "created": r.created.isoformat(),
                    }
                    for r in Report.objects.filter(owner=who).order_by("-created")[:100]
                ]
            }
        )
    data = body(request)
    seq = get_object_or_404(Sequence, pk=data.get("sequence"))
    title = str(data.get("title", "Untitled investigation")).strip()[:160]
    marks = [c.data for c in Candidate.objects.filter(owner=who, sequence=seq).order_by("updated")[:200]]
    snapshot = {
        "title": title,
        "sequence": inspect_manifest(seq.manifest),
        "candidates": marks,
        "settings": data.get("settings", {}),
        "analyses": [
            {"id": str(j.id), "method": j.kind, "selection": j.selection, "result": j.result}
            for j in Job.objects.filter(owner=who, state="completed", kind="motion", selection__sequence=str(seq.id))[
                :100
            ]
        ],
        "limitations": seq.manifest["warnings"],
        "retention": "Pinned while report exists. Private drafts belong to this browser session; loss of cookie loses editing access.",
    }
    if len(json.dumps(snapshot)) > 2 * 1024 * 1024:
        raise ValueError("Report exceeds size limit")
    with transaction.atomic():
        if data.get("parent"):
            parent = get_object_or_404(Report.objects.select_for_update(), pk=data["parent"], owner=who)
            root = parent.root or parent
            latest = Report.objects.filter(root=root).order_by("-revision").first() or root
            if latest.id != parent.id:
                return JsonResponse(
                    {
                        "error": {
                            "code": "revision_conflict",
                            "message": "A newer report revision exists. Open the latest revision before continuing.",
                        }
                    },
                    status=409,
                )
            r = Report.objects.create(
                owner=who, sequence=seq, snapshot=snapshot, parent=parent, root=root, revision=parent.revision + 1
            )
        else:
            r = Report.objects.create(owner=who, sequence=seq, snapshot=snapshot)
    return JsonResponse(report_data(r), status=201)


@api(["GET"])
def report(request, pk):
    return JsonResponse(report_data(get_object_or_404(Report, pk=pk, owner=owner(request))))


@require_GET
def report_page(request, pk):
    r = get_object_or_404(Report, pk=pk, owner=owner(request))
    if request.GET.get("format") == "json":
        response = JsonResponse(report_data(r))
        response["Cache-Control"] = "private, no-store"
        return response
    return render(request, "report.html", {"report": r, "frames": r.snapshot["sequence"]["frames"]})


@api(["POST", "DELETE"])
def shares(request, pk):
    r = get_object_or_404(Report, pk=pk, owner=owner(request))
    if request.method == "DELETE":
        Share.objects.filter(report=r).update(revoked=True)
        return JsonResponse({"revoked": True})
    token = secrets.token_urlsafe(32)
    Share.objects.create(token_hash=hashlib.sha256(token.encode()).hexdigest(), report=r)
    return JsonResponse({"url": "/shared/" + token, "embed": "/embed/" + token}, status=201)


def shared_report(token):
    return get_object_or_404(
        Share.objects.select_related("report"), token_hash=hashlib.sha256(token.encode()).hexdigest(), revoked=False
    ).report


@require_GET
def shared(request, token):
    r = shared_report(token)
    if request.GET.get("format") == "json":
        response = JsonResponse(report_data(r))
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response
    response = render(
        request,
        "embed.html" if request.path.startswith("/embed/") else "report.html",
        {
            "report": r,
            "frames": r.snapshot["sequence"]["frames"],
            "embedded": request.path.startswith("/embed/"),
            "shared": True,
        },
    )
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    if request.path.startswith("/embed/"):
        response.xframe_options_exempt = True
        response["Content-Security-Policy"] = "default-src 'self'; script-src 'none'; frame-ancestors 'self'"
    return response


@api(["GET", "POST"])
def reviews(request, pk):
    r = get_object_or_404(Report, pk=pk)
    if r.owner != owner(request):
        token = request.GET.get("share", "")
        if shared_report(token).id != r.id:
            raise Http404
    if request.method == "POST":
        text = str(body(request).get("text", "")).strip()
        if not 1 <= len(text) <= 4000:
            raise ValueError("Review must contain 1–4000 characters")
        Review.objects.create(report=r, owner=owner(request), text=text)
    return JsonResponse(
        {
            "reviews": [
                {"text": x.text, "created": x.created.isoformat(), "independent_session": x.owner != r.owner}
                for x in Review.objects.filter(report=r)[:100]
            ],
            "warning": "Agreement is not scientific confirmation. Session independence is not verified identity.",
        }
    )


@api(["GET"])
def health(request):
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse(
        {"status": "ok", "database": connection.vendor, "queued": Job.objects.filter(state="queued").count()}
    )


@api(["GET", "POST"])
def hips_cube(request):
    from .providers import locate_hips_cube_tile

    if request.method == "POST":
        b = body(request)
        ra = float(b.get("ra", 0))
        dec = float(b.get("dec", 0))
        layer = int(b.get("layer", 62))
    else:
        ra = float(request.GET.get("ra", 0))
        dec = float(request.GET.get("dec", 0))
        layer = int(request.GET.get("layer", 62))

    if not -90 <= dec <= 90:
        raise ValueError("Declination must be between -90 and +90 degrees")
    ra = ra % 360.0
    if not 0 <= layer < 102:
        raise ValueError("HiPS cube spectral layer must be between 0 and 101")

    info = locate_hips_cube_tile(ra, dec, layer=layer)
    return JsonResponse(info)
