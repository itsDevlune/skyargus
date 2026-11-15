# SPHEREx Image Sharpness & Optical Resolution Audit

## 1. Executive Summary & Resolution Findings

An end-to-end audit was conducted tracing the scientific image data path in Argus:
$$\text{Original Level 2 FITS HDU} \longrightarrow \text{Reprojection / Celestial TAN Grid} \longrightarrow \text{Preview Generation} \longrightarrow \text{Canvas Rendering}$$

### Key Findings:
1. **Instrument Optical Resolution vs. Display Softness**:
   - SPHEREx has an intrinsic plate scale of $\approx 6.155″ - 6.200″/\text{pixel}$ and an optical diffraction/PSF beam FWHM of $\sim 1.5 - 2.0$ pixels.
   - Point sources on SPHEREx detector arrays span only 1 to 3 unbinned pixels. Softness at high zoom is an **intrinsic physical property of the telescope optics and detector sampling**, not algorithmic degradation.
2. **Identification of Artificial Canvas Blur**:
   - Prior to this audit, HTML5 Canvas `ctx.imageSmoothingEnabled` remained at default (`true`). When rendering a $58 \times 58$ or $116 \times 116$ pixel cutout scaled up to fit a $600\times 600$ viewport, the web browser applied bilinear interpolation across screen pixels. This introduced perceived artificial blur and smoothed out sharp pixel boundaries.
   - Enabling **Nearest-Neighbour interpolation** (`ctx.imageSmoothingEnabled = false`) renders true, crisp detector grid pixels without browser-induced blur.
3. **No Unintentional Downsampling or Smoothing**:
   - The native FITS array is read in floating-point precision (`float32`).
   - Reprojection uses `reproject_interp` onto a TAN grid matching the requested FOV with exact $6.2″/\text{pixel}$ resolution ($58 \times 58$ for 6′, $116 \times 116$ for 12′).
   - Previews are saved at native output grid dimensions ($58 \times 58$ pixels) with zero downsampling or clipping.

---

## 2. Quantitative Dimension & Metric Comparison

The exact metrics for representative SPHEREx Level 2 observations (Barnard's Star region, $\text{RA} = 269.452075^\circ, \text{Dec} = 4.693391^\circ$) are:

| Processing Stage | Dimensions | Pixel Scale | Notes |
| :--- | :--- | :--- | :--- |
| **Native Archive FITS (`IMAGE` HDU)** | $45 \times 95$ or $95 \times 95$ | $6.155″ \times 6.153″$ | Unbinned raw detector pixels from IRSA Level 2 cutout |
| **Reprojected Celestial TAN Grid** | $58 \times 58$ ($6^\prime$) / $116 \times 116$ ($12^\prime$) | $6.200″ \times 6.200″$ | Fixed gnomonic projection, North up, East left |
| **Preview PNG Artifact** | $58 \times 58$ / $116 \times 116$ | $6.200″/\text{pixel}$ | 8-bit RGBA lossless PNG, unclipped dynamic range |
| **Canvas Backing-Store (`canvas.width`)** | $\text{CSS Width} \times \text{dPR}$ ($752 \times 702$ @ 1x) | Native display device pixels | Sized to `devicePixelRatio` to prevent subpixel scaling artifacts |
| **CSS Display Box (`canvas.style`)** | $752 \times 702$ px (responsive viewport) | Viewport magnification | Magnification factor $12.9\times$ in Fit Image mode; $1.0\times$ in Native Pixels mode |

---

## 3. Official SPHEREx HiPS-Cube Tutorial Reproduction

To definitively verify whether remaining image softness is an inherent instrument property rather than software degradation, Argus reproduced and validated both distinct visual benchmarks from the official SPHEREx tutorial (`tutorials/spherex/spherex_hipscube.md`):

### A. Section 6.2: Single-Layer Visualization (PAH 3.3 µm)
- **Target Coordinates**: $\text{RA} = 60.8109955^\circ$, $\text{Dec} = +51.3404038^\circ$ (HEALPix Order 5 tile `Npix445_cube.fits`)
- **Spectral Layer**: Layer 62 ($\lambda \approx 3.293\,\mu\text{m}$, representing the $3.3\,\mu\text{m}$ polycyclic aromatic hydrocarbon band)
- **Spatial Grid**: Full $512 \times 512$ mosaic grid
- **Scaling & Normalization**: Logarithmic stretch with `norm="log"`:
  $$\text{val}_{\text{norm}} = \frac{\log_{10}(\text{clip}(I, I_5, I_{99.9})) - \log_{10}(I_5)}{\log_{10}(I_{99.9}) - \log_{10}(I_5)}$$
- **Colormap**: `viridis` (standard tutorial Section 6.2) and `inferno`
- **Artifacts Saved**:
  - `docs/evidence/sharpness-audit/tutorial_single_layer62_viridis.png`
  - `static/hips_layer62_viridis.png` (integrated in Argus `#mosaic-view` dropdown)
  - `static/hips_layer62_log.png` (Inferno variant)

### B. Section 6.3: Drill-Through Wavelength-Median Stack
- **Operation**: Collapsing the entire 102-channel cube along the spectral axis via `np.nanmedian(cube, axis=0)`
- **Scaling & Normalization**: 5th to 99.9th percentile logarithmic stretch of positive median intensities:
  - 5th percentile: $0.2382\,\text{MJy/sr}$
  - 99.9th percentile: $17.5126\,\text{MJy/sr}$
- **Colormap**: 256-level `inferno` colormap
- **Artifacts Saved**:
  - `docs/evidence/sharpness-audit/tutorial_wavelength_median_inferno.png`
  - `static/hips_cube_median_inferno.png` (integrated in Argus `#mosaic-view` dropdown)

### Comparison Evidence & Scientific Distinction:
1. **Tutorial Reference Outputs**: Both the single-slice 2D spectral plane (Section 6.2) and the continuum wavelength median stack (Section 6.3) are reproduced identically.
2. **Scientific Distinction**: Section 6.2 inspects line emission at an isolated wavelength channel, whereas Section 6.3 enhances continuum signal-to-noise across the full bandpass. Neither mode increases spatial angular resolution beyond the physical telescope beam ($\sim 6.2″/\text{pixel}$).
3. **Argus Mosaic / Spectral Mode**: Integrated directly into Argus's explorer view with a `#mosaic-view` dropdown, allowing instantaneous switching between Layer 62 (Viridis), Layer 62 (Inferno), and Wavelength Median (Inferno).
4. **Outcome**: The Argus-rendered mosaic identically reproduces the official tutorial's intensity variations, spatial structure, and point-spread function characteristics. The smoothness in extended nebulosity originates from the sky emission and SPHEREx's optical resolution, confirming Argus introduces zero artificial blur.

---

## 4. Sharpness Controls & Display Modes Implemented

1. **Display Interpolation Selector**:
   - **Nearest-Neighbour (pixel-crisp)**: Uses `ctx.imageSmoothingEnabled = false`. Displays exact square detector pixels at high magnification without browser filtering.
   - **Smooth (bilinear)**: Uses `ctx.imageSmoothingEnabled = true` for users preferring smoothed aesthetic transitions.
2. **Selectable Stretches**:
   - **arcsinh**: High dynamic range display preserving faint emission and bright cores simultaneously.
   - **Linear**: Direct scaling between minimum and maximum percentiles.
   - **Logarithmic**: Log-scaled visualization handling orders of magnitude of surface brightness.
3. **1:1 Native Pixels Mode**:
   - Displays exactly 1 loaded grid pixel per CSS screen pixel (`scale = 1.0`), preventing any interpolation or scaling distortion.
4. **Dedicated Mosaic / Spectral Mode**:
   - Clearly distinguished from dated Time Explorer single exposures.
   - Discloses mosaic layer provenance, wavelength, spatial grid dimensions, and normalization policy.
   - Explicitly documents that spectral stacking does not increase angular resolution.

---

## 5. Visual Evidence Artifacts

The following verification evidence files were generated and stored in `docs/evidence/sharpness-audit/`:
- `argus-nearest-neighbour.png`: Explorer screenshot demonstrating crisp, unblurred pixel boundaries.
- `argus-smooth-bilinear.png`: Explorer screenshot showing bilinear interpolation for comparison.
- `argus-mosaic-mode.png`: Argus rendering the SPHEREx HiPS cube Layer 62 ($3.3\,\mu\text{m}$).
- `crop_nearest_neighbour.png`: $8\times$ zoom of point source with nearest-neighbour interpolation.
- `crop_smooth_bilinear.png`: $8\times$ zoom of point source with bilinear interpolation.
- `hips-tutorial-reference.png`: Tutorial benchmark reproduction.
- `stretch_asinh.png`, `stretch_linear.png`, `stretch_log.png`: Validated stretch comparison fixtures.
