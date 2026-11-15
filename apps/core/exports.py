import io

from astropy.io import fits
from astropy.wcs import WCS
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from PIL import Image, ImageDraw
from PIL.PngImagePlugin import PngInfo

from .models import Artifact, Report


@require_GET
def report_export(request, pk, format):
    from .views import owner

    report = get_object_or_404(Report, pk=pk, owner=owner(request))
    if format not in ("png", "gif"):
        return HttpResponse("Supported formats: png, gif", status=400)
    manifest = report.snapshot["sequence"]
    frames = manifest["frames"]
    if not frames:
        return HttpResponse("No usable image evidence", status=422)
    if format == "png":
        index = report.snapshot.get("settings", {}).get("index", 0)
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(frames):
            return HttpResponse(
                "The report selected frame is invalid; save a new report revision with a valid frame.", status=422
            )
        selected_frames = [(index, frames[index])]
    else:
        selected_frames = list(enumerate(frames))
    images = []
    for index, frame in selected_frames:
        artifact = get_object_or_404(Artifact, pk=frame["preview"]["id"])
        with Image.open(settings.DATA_ROOT / artifact.filename) as native:
            native = native.convert("RGBA")
            native.thumbnail((800, 800))
            scale = min(4, 800 / max(native.size))
            native = native.resize((round(native.width * scale), round(native.height * scale)))
            image = Image.new("RGB", (max(650, native.width), native.height + 100), (8, 11, 16))
            image.paste(native, (0, 0), native)
        draw = ImageDraw.Draw(image)
        y = native.height + 8
        for line in [
            f"ARGUS | {'REAL' if manifest.get('data_mode', 'real') == 'real' else 'SIMULATED'} {frame['source']} {frame['release']} | {frame['date']}",
            frame["id"],
            f"Units: {frame['units']} | WCS residual / spectral comparability: not assessed",
            "Display stretch only. Manual marks are unconfirmed. See immutable JSON for full provenance.",
        ]:
            draw.text((10, y), line, fill="white")
            y += 20
        if manifest["geometry"].get("mode", "celestial") == "celestial":
            w = WCS(fits.Header.fromstring(manifest["geometry"]["wcs"]))
            for mark in report.snapshot["candidates"]:
                if mark["frame"] == index:
                    x, y = w.world_to_pixel_values(mark["ra"], mark["dec"])
                    x = (x + 0.5) * native.width / manifest["geometry"]["width"]
                    y = (manifest["geometry"]["height"] - 0.5 - y) * native.height / manifest["geometry"]["height"]
                    draw.ellipse((x - 5, y - 5, x + 5, y + 5), outline="#8eb8ff", width=2)
        images.append(image)
    out = io.BytesIO()
    if format == "gif":
        images[0].save(out, format="GIF", save_all=True, append_images=images[1:], duration=1200, loop=0, disposal=2)
    else:
        metadata = PngInfo()
        selected_index, selected_frame = selected_frames[0]
        for key, value in {
            "ArgusReport": str(report.id),
            "FrameIndex": str(selected_index),
            "ObservationID": selected_frame["id"],
            "Observed": selected_frame["date"],
            "DataMode": manifest.get("data_mode", "real"),
        }.items():
            metadata.add_text(key, str(value))
        images[0].save(out, format="PNG", pnginfo=metadata)
    response = HttpResponse(out.getvalue(), content_type="image/" + format)
    response["Content-Disposition"] = f'attachment; filename="argus-{report.id}.{format}"'
    response["Cache-Control"] = "private, no-store"
    return response
