import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import io

from astropy.io import fits

from apps.core.network import get

raw = get("https://ws.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/data/pub/NEOSSAT/NEOS_SCI_2019312133024.fits")
Path("data/neossat-example.fits").write_bytes(raw)
h = fits.open(io.BytesIO(raw))
h.info()
print(repr(h[0].header))
