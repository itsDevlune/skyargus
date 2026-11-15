"""Read existing geometry, then one bounded live 12' request through the real API/worker."""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','argus.settings')
import django

django.setup()
import requests
from astropy.io import fits
from astropy.wcs import WCS
from django.conf import settings

from apps.core.models import Artifact, Sequence
from science.geometry import footprint, inspect_manifest

directory=Path('docs/evidence/explorer-redesign')
directory.mkdir(parents=True,exist_ok=True)
audit=[]
for seq in Sequence.objects.all():
    m=inspect_manifest(seq.manifest)
    row={'sequence':str(seq.id),'source':m['selection']['source'],'requested':[m['selection']['width'],m['selection']['height']],'recorded_pixels':[m['geometry']['width'],m['geometry']['height']],'inspection':m['inspection']}
    if m['frames'] and m['geometry'].get('mode')!='native':
        artifact=Artifact.objects.get(pk=m['frames'][0]['aligned']['id'])
        with fits.open(settings.DATA_ROOT/artifact.filename) as h:
            row['actual_fits_pixels']=[h[0].header['NAXIS1'],h[0].header['NAXIS2']]
            row['actual_fits_footprint']=footprint(WCS(h[0].header),h[0].data.shape)
    audit.append(row)
(directory/'geometry-audit.json').write_text(json.dumps(audit,indent=2),encoding='utf8')
print('Existing cache audit:',[(r['requested'],r['recorded_pixels'],r['source']) for r in audit],flush=True)
base='http://127.0.0.1:8000'
session=requests.Session()
session.get(base+'/',timeout=10)
session.headers['X-CSRFToken']=session.cookies.get('csrftoken','')
payload={'ra':269.452075,'dec':4.693391,'unit':'deg','width':12,'height':12,'source':'spherex','release':'dr1','detector':3}
r=session.post(base+'/api/v1/searches',json=payload,timeout=15)
r.raise_for_status()
result=r.json()
last=None
for _ in range(180):
    if result.get('sequence'):
        break
    job=session.get(base+result['status_url'],timeout=10).json()
    if job['stage']!=last:
        print(job['state'],job['stage'],flush=True)
        last=job['stage']
    if job['state'] in ('completed','partial'):
        result=job['result']
        break
    if job['state'] in ('failed','cancelled'):
        (directory/'live12-failure.json').write_text(json.dumps(job,indent=2),encoding='utf8')
        raise RuntimeError(str(job['error']))
    time.sleep(2)
else:
    raise RuntimeError('Bounded verification wait expired; persistent job remains inspectable')
manifest=session.get(base+'/api/v1/sequences/'+result['sequence'],timeout=15).json()
(directory/'live12-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
assert manifest['geometry']['width']==116 and manifest['geometry']['height']==116
assert manifest['inspection']['request_grid_consistent']
print('VERIFIED',result['sequence'],len(manifest['frames']),'frames',manifest['inspection'],flush=True)
