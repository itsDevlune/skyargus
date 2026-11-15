from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from science.coordinates import region
from science.cubes import channel_png, pixel_spectrum, sky_spectrum

from .models import Artifact, Sequence
from .views import api, body, enqueue


@api(['POST'])
def load_cube(request):
    selection = region(body(request))
    if selection['source'] != 'spherex':
        raise ValueError('Cube exploration requires SPHEREx')
    return enqueue(request, selection, 'cube')


def cube_path(pk):
    sequence = get_object_or_404(Sequence, pk=pk)
    meta = sequence.manifest.get('cube')
    if not meta:
        raise ValueError('Not a cube dataset')
    artifact = get_object_or_404(Artifact, pk=meta['artifact']['id'], sequence=sequence)
    path = settings.DATA_ROOT / artifact.filename
    if not path.is_file():
        raise Http404('Stored cube artifact is unavailable')
    return path


@api(['GET'])
def plane(request, pk, index):
    reference = int(request.GET['reference']) if 'reference' in request.GET else None
    return HttpResponse(channel_png(cube_path(pk), index, request.GET.get('coverage') == '1', reference), content_type='image/png')


@api(['POST'])
def spectrum(request, pk):
    data = body(request)
    if 'ra' in data or 'dec' in data:
        return JsonResponse(sky_spectrum(cube_path(pk), float(data['ra']), float(data['dec'])))
    x, y = data.get('x'), data.get('y')
    if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, int) or not isinstance(y, int):
        raise ValueError('Integer FITS pixel x/y required')
    return JsonResponse(pixel_spectrum(cube_path(pk), x, y))
