import { $, api, toast } from "./common.js";

async function loadHipsNeighbors(ra, dec) {
  if (!ra || !dec) return;
  try {
    const res = await api(`/api/v1/hips/cube?ra=${encodeURIComponent(ra)}&dec=${encodeURIComponent(dec)}`);
    if (res) {
      // Store center tile
      if (res.png_url && res.center) {
        state.hipsCenterTile = res;
        if (!state.hipsTileImages.has(res.ipix)) {
          const img = new Image();
          img.src = res.png_url;
          img.onload = () => draw();
          state.hipsTileImages.set(res.ipix, { img, meta: res });
        }
      }
      if (res.neighbor_tiles) {
        state.hipsNeighbors = res.neighbor_tiles;
        for (const t of res.neighbor_tiles) {
          if (!state.hipsTileImages.has(t.ipix)) {
            const img = new Image();
            img.src = t.png_url;
            img.onload = () => draw();
            state.hipsTileImages.set(t.ipix, { img, meta: t });
          }
        }
      }
      draw();
    }
  } catch (e) {
    console.warn("Could not preload HiPS neighbor tiles:", e);
  }
}

const state = {
  manifest: null,
  index: 0,
  b: 0,
  images: new Map(),
  marks: [],
  gaia: [],
  wise: [],
  zoom: 1,
  panX: 0,
  panY: 0,
  tool: "pan",
  selected: null,
  editing: null,
  playing: false,
  timer: null,
  job: null,
  generation: 0,
  controller: null,
  resolved: null,
  viewMode: "fit",
  targetPos: null,
  targetName: null,
  showTarget: true,
  showHips: true,
  hipsNeighbors: [],
  hipsTileImages: new Map(),
  cursorPoint: null,
};
const canvas = $("viewer"),
  ctx = canvas.getContext("2d");
let transform = null,
  drag = null;
function selection() {
  return Object.fromEntries(
    [
      "source",
      "unit",
      "ra",
      "dec",
      "width",
      "height",
      "release",
      "detector",
      "start",
      "end",
    ].map((k) => [k, $(k).value]),
  );
}
function busy(value) {
  $("search-form")
    .querySelectorAll("input,select,button")
    .forEach((control) => {
      control.disabled = value;
    });
  $("cancel").disabled = false;
  if (!value && $("source").value === "neossat")
    $("release").disabled = $("detector").disabled = true;
  $("cancel").hidden = !value;
}
function openPanel(name) {
  const panel = $("workspace-panel");
  panel.hidden = false;
  panel.dataset.kind = name;
  panel.style.top = "";
  for (const [type, id] of [
    ["evidence", "evidence-panel"],
    ["observations", "observations-panel"],
    ["analysis", "analysis-content"],
  ]) {
    $(id).hidden = type !== name;
    $("open-" + type).setAttribute("aria-pressed", String(type === name));
  }
  $("panel-title").textContent = {
    evidence: state.selected ? "Source evidence" : "Observation evidence",
    observations: "Observations",
    analysis: "Analysis",
  }[name];
  updateAnalysisContext();
}
function closePanel() {
  const active = ["evidence", "observations", "analysis"].find(
    (name) => $("open-" + name).getAttribute("aria-pressed") === "true",
  );
  const returnFocus = $("workspace-panel").contains(document.activeElement);
  $("workspace-panel").hidden = true;
  for (const n of ["evidence", "observations", "analysis"])
    $("open-" + n).setAttribute("aria-pressed", "false");
  if (returnFocus && active) $("open-" + active).focus();
}
for (const name of ["evidence", "observations", "analysis"])
  $("open-" + name).onclick = () => {
    if (
      !$("workspace-panel").hidden &&
      $("open-" + name).getAttribute("aria-pressed") === "true"
    )
      closePanel();
    else openPanel(name);
  };
$("close-panel").onclick = closePanel;
if ($("expand-panel")) $("expand-panel").onclick = () => {
  const expanded = $("workspace-panel").dataset.expanded !== 'true';
  $("workspace-panel").dataset.expanded = String(expanded);
  $("expand-panel").setAttribute('aria-expanded', String(expanded));
  $("expand-panel").textContent = expanded ? 'Restore panel' : 'Expand panel';
};
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closePanel();
});
function updateAnalysisContext() {
  if (!state.manifest) {
    $("analysis-context").textContent =
      "Load a field, then select a source or region.";
    return;
  }
  if (state.manifest.geometry.mode === "native") {
    $("analysis-context").textContent =
      "Native detector pixels: celestial motion fitting is unavailable without validated WCS and tracking corrections. Viewport is retained between panels.";
    return;
  }
  const p = state.selected;
  $("analysis-context").textContent = p
    ? `Selected ICRS ${p.ra.toFixed(6)}°, ${p.dec.toFixed(6)}° · frame ${state.index + 1}. Selection and viewport are retained between panels.`
    : `Loaded field ${state.manifest.selection.ra.toFixed(5)}°, ${state.manifest.selection.dec.toFixed(5)}° · select a source with Mark. Frames remain separate exposures.`;
}
function bandpassSummary(a, b) {
  if (!a) return "No image loaded";
  if ($("mode").value === "single")
    return "Single dated exposure · not combined";
  if (!b) return "Comparison not assessed";
  if (a.id === b.id) return "A and B are the same exposure";
  const wa = a.wavelength,
    wb = b.wavelength;
  if (!wa || !wb || ![...wa, ...wb].every((v) => Number.isFinite(v) && v > 0))
    return "A/B bandpass overlap not assessed";
  const overlap =
    Math.max(
      0,
      Math.min(wa[0] + wa[1] / 2, wb[0] + wb[1] / 2) -
        Math.max(wa[0] - wa[1] / 2, wb[0] - wb[1] / 2),
    ) / Math.min(wa[1], wb[1]);
  $("bandpass-summary").title =
    "Field-center visualization bandpass overlap, not calibrated response or photometric comparability. Same detector alone is insufficient.";
  return overlap > 0
    ? `A/B display-band overlap ${(overlap * 100).toFixed(0)}% · calibration not assessed`
    : "A/B display bands do not overlap · avoid brightness comparison";
}
function updateRequestState() {
  const m = state.manifest;
  if (!m) {
    $("request-pending").hidden = true;
    return;
  }
  const s = selection();
  const unchangedName =
    !$("object").value.trim() ||
    $("object").value.trim() === state.resolvedQuery;
  const same =
    unchangedName &&
    [
      "source",
      "release",
      "detector",
      "width",
      "height",
      "unit",
      "ra",
      "dec",
      "start",
      "end",
    ].every((k) =>
      ["width", "height", "ra", "dec", "detector"].includes(k)
        ? Math.abs(Number(s[k]) - Number(m.selection[k])) < 1e-7
        : String(s[k] || "") === String(m.selection[k] || ""),
    );
  $("request-pending").hidden = same;
  $("search-form").classList.toggle("request-dirty", !same);
}
$("search-form").addEventListener("input", updateRequestState);
$("search-form").addEventListener("change", updateRequestState);
function status(text) {
  $("status").textContent = text;
}
function stop() {
  state.playing = false;
  clearTimeout(state.timer);
  $("play").textContent = "▶";
}
function safeError(e) {
  if (e.name !== "AbortError") {
    status(e.message);
    toast(e.message);
  }
}
let lookupGeneration = 0;
async function resolve(signal) {
  const generation = ++lookupGeneration;
  const name = $("object").value.trim();
  if (!name) throw Error("Enter an object name to resolve.");
  status("Resolving reference position…");
  state.resolved = null;
  state.resolvedQuery = null;
  state.targetPos = null;
  state.targetName = null;
  $("ra").value = "";
  $("dec").value = "";
  $("identity").textContent = "Resolving reference position…";
  draw();
  let data;
  try {
    data = await api("/api/v1/resolve", { name }, "POST", signal);
  } catch (error) {
    if (generation !== lookupGeneration || $("object").value.trim() !== name)
      return;
    throw error;
  }
  if (generation !== lookupGeneration || $("object").value.trim() !== name)
    return;
  state.resolved = data;
  state.resolvedQuery = name;
  $("ra").value = data.ra.toFixed(8);
  $("dec").value = data.dec.toFixed(8);
  $("unit").value = "deg";
  $("identity").textContent = `${data.name} · ${data.resolver} · ${data.epoch}`;
  state.targetPos = { ra: data.ra, dec: data.dec };
  state.targetName = data.name;
  status("Reference position resolved");
  updateRequestState();
  draw();
}
$("resolve").onclick = () => resolve().catch(safeError);
$("targets").onclick = async (e) => {
  const b = e.target.closest("[data-name]");
  if (b) {
    $("object").value = b.dataset.name;
    try {
      await resolve();
    } catch (e) {
      safeError(e);
    }
  }
};
$("fov-presets").onclick = (e) => {
  const b = e.target.closest("[data-fov]");
  if (b) {
    $("width").value = $("height").value = b.dataset.fov;
    updateRequestState();
  }
};
const sleep = (ms, signal) =>
  new Promise((resolve, reject) => {
    const t = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(t);
        reject(new DOMException("Aborted", "AbortError"));
      },
      { once: true },
    );
  });
async function waitJob(job, gen, signal) {
  state.job = job.job;
  for (;;) {
    const j = await api(job.status_url, undefined, "GET", signal);
    if (gen !== state.generation) throw new DOMException("Stale", "AbortError");
    status(j.stage);
    if (["completed", "partial"].includes(j.state)) return j.result;
    if (["failed", "cancelled"].includes(j.state))
      throw Error(j.error?.message || "Request cancelled");
    await sleep(1200, signal);
  }
}
$("search-form").onsubmit = async (e) => {
  e.preventDefault();
  stop();
  state.controller?.abort();
  const controller = new AbortController();
  state.controller = controller;
  const gen = ++state.generation;
  busy(true);
  status("Validating archive request…");
  try {
    if (
      !state.retrySequence &&
      $("object").value.trim() &&
      $("object").value.trim() !== state.resolvedQuery
    )
      await resolve(controller.signal);
    let r = await api(
      "/api/v1/searches",
      {
        ...selection(),
        ...(state.retrySequence ? { retry_sequence: state.retrySequence } : {}),
      },
      "POST",
      controller.signal,
    );
    if (r.job) r = await waitJob(r, gen, controller.signal);
    if (gen !== state.generation) return;
    const m = await api(
      "/api/v1/sequences/" + r.sequence,
      undefined,
      "GET",
      controller.signal,
    );
    await loadManifest(m);
  } catch (e) {
    safeError(e);
  } finally {
    state.retrySequence = null;
    if (gen === state.generation) {
      busy(false);
      state.job = null;
    }
  }
};
$("cancel").onclick = async () => {
  const job = state.job;
  state.controller?.abort();
  ++state.generation;
  busy(false);
  state.job = null;
  if (job)
    try {
      await api("/api/v1/jobs/" + job, { action: "cancel" });
    } catch (e) {
      safeError(e);
    }
  status("Cancelled this request; existing evidence preserved");
};
async function loadManifest(m) {
  state.manifest = m;
  state.parentReport = params.get("parent") || null;
  if (m?.selection?.ra && m?.selection?.dec) {
    state.targetPos = { ra: Number(m.selection.ra), dec: Number(m.selection.dec) };
    state.targetName = $("object").value.trim() || state.resolvedQuery || null;
  }
  loadHipsNeighbors(m.selection.ra, m.selection.dec);
  for (const key of [
    "source",
    "unit",
    "ra",
    "dec",
    "width",
    "height",
    "release",
    "detector",
    "start",
    "end",
  ]) {
    if (m.selection[key] !== undefined) $(key).value = m.selection[key] ?? "";
  }
  const native = m.geometry.mode === "native";
  $("release").disabled = $("detector").disabled = native;
  const matchingIdentity =
    state.resolved &&
    Math.abs(state.resolved.ra - m.selection.ra) < 1e-6 &&
    Math.abs(state.resolved.dec - m.selection.dec) < 1e-6;
  if (!matchingIdentity) $("object").value = "";
  $("identity").textContent = native
    ? "Loaded NEOSSat raw detector observations. Search coordinates select coverage; image pixels are not registered celestial coordinates."
    : matchingIdentity
      ? `${state.resolved.name} · reference coordinates; proper motion not applied.`
      : "Loaded ICRS field. Resolve an object to identify its reference position.";
  $("cursor").textContent = native
    ? "Native detector coordinates; no celestial WCS"
    : "ICRS coordinate readout";
  document.querySelector(".analysis-panel").hidden =
    native || $("analysis-tool").value !== "motion";
  state.index = 0;
  state.b = Math.max(0, m.frames.length - 1);
  state.images.clear();
  state.marks = [];
  state.gaia = [];
  state.wise = [];
  $("gaia-result").textContent = "";
  $("wise-result").textContent = "";
  state.selected = null;
  state.editing = null;
  state.zoom = 1;
  state.viewMode = "fit";
  state.panX = state.panY = 0;
  $("field-title").textContent =
    `${matchingIdentity ? state.resolved.name + " · " : ""}${m.selection.ra.toFixed(4)}°, ${m.selection.dec.toFixed(4)}°`;
  $("release-label").textContent =
    `${m.selection.source.toUpperCase()} · ${m.selection.source === "neossat" ? "CADC raw" : m.selection.release.toUpperCase()}`;
  $("empty").hidden = m.frames.length > 0;
  $("empty").querySelector("h2,h3").textContent = m.frames.length
    ? ""
    : "No usable observations";
  $("empty").querySelector("p").textContent =
    m.discovery.warning ||
    "Try another detector, date range, release or field. No synthetic replacement is shown.";
  $("timeline").max = Math.max(0, m.frames.length - 1);
  $("observation-count").textContent = m.frames.length;
  for (const id of [
    "play",
    "next",
    "previous",
    "fit-image",
    "native-pixels",
    "zoom-in",
    "zoom-out",
    "reset",
    "timeline",
    "mark",
  ])
    $(id).disabled = true;
  const time = m.inspection?.time;
  const dates = m.frames.map((f) => Date.parse(f.date)).filter(Number.isFinite);
  const days =
    time?.baseline_days ??
    (dates.length
      ? (Math.max(...dates) - Math.min(...dates)) / 86400000
      : null);
  $("baseline").textContent =
    days === null
      ? "Baseline not assessed"
      : `Baseline ${days < 1 ? (days * 24).toFixed(2) + " h" : days.toFixed(2) + " d"}`;
  const output = m.inspection?.output;
  const width =
    output?.width_arcmin ??
    m.geometry.width * Math.abs(m.geometry.cdelt?.[0] || 0) * 60;
  const height =
    output?.height_arcmin ??
    m.geometry.height * Math.abs(m.geometry.cdelt?.[1] || 0) * 60;
  $("geometry-summary").textContent = native
    ? `Loaded native detector · ${m.geometry.width} × ${m.geometry.height} pixels · sky footprint not assessed`
    : `Loaded request ${m.selection.width}′ × ${m.selection.height}′ · WCS grid ${width.toFixed(2)}′ × ${height.toFixed(2)}′`;
  if (m.inspection?.request_grid_consistent === false)
    $("geometry-summary").textContent += " · WARNING: request/grid mismatch";
  $("observation-policy").textContent =
    (m.discovery.selection || "Selection policy not recorded") +
    ". " +
    (m.discovery.coverage_warning ||
      "Archive-wide coverage is not established.") +
    " Frames are indexed in chronological order; playback gaps are not to scale.";
  $("ab").replaceChildren();
  m.frames.forEach((f, i) => {
    const o = document.createElement("option");
    o.value = i;
    o.textContent = `${i + 1} · ${f.date || "Unknown date"}`;
    $("ab").append(o);
  });
  $("ab").value = state.b;
  $("first-date").textContent = m.frames[0]?.date?.slice(0, 10) || "—";
  $("last-date").textContent = m.frames.at(-1)?.date?.slice(0, 10) || "—";
  $("frame-summary").textContent =
    `${m.frames.length} observations · ${m.excluded.length} excluded`;
  renderRows();
  await refreshMarks();
  await frame(
    Math.max(
      0,
      Math.min(m.frames.length - 1, Number(params.get("frame")) || 0),
    ),
  );
  if (["single", "blink", "side", "swipe"].includes(params.get("mode")))
    $("mode").value = params.get("mode");
  if (params.has("zoom"))
    state.zoom = Math.max(0.5, Math.min(12, Number(params.get("zoom")) || 1));
  if (
    params.has("viewMode") &&
    ["fit", "native", "custom"].includes(params.get("viewMode"))
  )
    state.viewMode = params.get("viewMode");
  else if (params.has("zoom")) state.viewMode = "custom";
  if (params.has("b"))
    state.b = Math.max(
      0,
      Math.min(m.frames.length - 1, Number(params.get("b")) || 0),
    );
  $("ab").value = state.b;
  if (params.has("contrast"))
    $("stretch").value = Math.max(
      0.5,
      Math.min(2, Number(params.get("contrast")) || 1),
    );
  const restoredPan = constrainPan(
    Number(params.get("panX")) || 0,
    Number(params.get("panY")) || 0,
  );
  state.panX = restoredPan.x;
  state.panY = restoredPan.y;
  await frame(state.index);
  for (const id of [
    "play",
    "next",
    "previous",
    "fit-image",
    "native-pixels",
    "zoom-in",
    "zoom-out",
    "reset",
    "timeline",
    "mark",
  ])
    $(id).disabled = !m.frames.length;
  $("request-details").open = false;
  updateRequestState();
  updateAnalysisContext();
  status(
    m.frames.length === 0
      ? "No coverage / no usable cutouts"
      : m.frames.length === 1
        ? "Single observation · time comparison unavailable"
        : `${m.frames.length} frames${m.excluded.length ? ` · ${m.excluded.length} unavailable` : ""} · ${native ? "native detector view" : "compare filter response before interpreting changes"}`,
  );
}
async function imageAt(i) {
  if (state.images.has(i)) return state.images.get(i);
  const m = state.manifest;
  if (!m?.frames[i]) return null;
  const image = new Image();
  image.src = m.frames[i].preview.url;
  await image.decode();
  if (state.manifest !== m) return null;
  if (
    image.naturalWidth !== m.geometry.width ||
    image.naturalHeight !== m.geometry.height
  )
    throw Error(
      "Preview dimensions do not match the recorded WCS grid. This image cannot be mapped safely.",
    );
  state.images.set(i, image);
  while (state.images.size > 3) {
    const k = [...state.images.keys()].find(
      (k) => k !== state.index && k !== state.b,
    );
    if (k === undefined) break;
    state.images.delete(k);
  }
  return image;
}
async function frame(i) {
  const m = state.manifest;
  if (!m?.frames.length) return;
  state.index = Math.max(0, Math.min(i, m.frames.length - 1));
  const selected = state.index;
  $("sky-label").textContent =
    m.geometry.mode === "native"
      ? "Native detector pixels · uncalibrated raw ADU"
      : `${m.geometry.width} × ${m.geometry.height} data pixels · 6.2″ / pixel · N up / E left`;
  document.querySelector(".orientation").hidden = m.geometry.mode === "native";
  $("timeline").value = selected;
  $("count").textContent = `${selected + 1} / ${m.frames.length}`;
  const f = m.frames[selected];
  const b = m.frames[state.b];
  $("bandpass-summary").textContent = bandpassSummary(f, b);
  const fraction = Number(f.coverage_fraction);
  const coverage = Number.isFinite(fraction)
    ? ` · valid ${(fraction * 100).toFixed(1)}%`
    : "";
  $("sky-label").textContent += coverage;
  $("frame-summary").textContent =
    `${f.date || "Date unknown"} · ${selected + 1}/${m.frames.length}`;
  evidence(f);
  updateAnalysisContext();
  await imageAt(selected);
  if ($("mode").value !== "single") await imageAt(state.b);
  if (selected === state.index) draw();
}
let mosaicImage = null;
async function getMosaicImage() {
  if (mosaicImage) return mosaicImage;
  const img = new Image();
  img.src = "/static/hips_layer62_log.png";
  await img.decode();
  mosaicImage = img;
  return img;
}
function resize() {
  const dpr = devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.round(rect.width * dpr);
  canvas.height = Math.round(rect.height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.imageSmoothingEnabled = $("interpolation")?.value === "smooth";
  const pan = constrainPan(state.panX, state.panY);
  state.panX = pan.x;
  state.panY = pan.y;
  draw();
}
new ResizeObserver(resize).observe($("sky"));
function geometry() {
  const m = state.manifest;
  const isMosaic = $("mode")?.value === "mosaic";
  if (!m && !isMosaic) return null;
  const box = canvas.getBoundingClientRect(),
    g = isMosaic ? { width: 512, height: 512 } : m.geometry;
  const baseScale = Math.min(box.width / g.width, box.height / g.height) * 0.96;
  const scale = state.viewMode === "native" ? 1 : baseScale * state.zoom;
  $("zoom-readout").textContent =
    state.viewMode === "fit" ? "Fit" : `${Math.round(scale * 100)}%`;
  return {
    scale,
    x: box.width / 2 - (g.width * scale) / 2 + state.panX,
    y: box.height / 2 - (g.height * scale) / 2 + state.panY,
    width: g.width * scale,
    height: g.height * scale,
    cw: box.width,
    ch: box.height,
  };
}
function constrainPan(x, y) {
  const g = state.manifest?.geometry;
  const box = canvas.getBoundingClientRect();
  if (!g) return { x: 0, y: 0 };
  let width, height, viewportWidth, viewportHeight;
  if ($("mode").value === "side") {
    const scale =
      state.viewMode === "native"
        ? 1
        : Math.min(
            (box.width / 2 - 24) / g.width,
            (box.height - 48) / g.height,
          ) * state.zoom;
    width = g.width * scale;
    height = g.height * scale;
    viewportWidth = box.width / 2;
    viewportHeight = box.height;
  } else {
    const t = geometry();
    if (!t) return { x: 0, y: 0 };
    width = t.width;
    height = t.height;
    viewportWidth = t.cw;
    viewportHeight = t.ch;
  }
  const maxX = Math.max(0, (width - viewportWidth) / 2);
  const maxY = Math.max(0, (height - viewportHeight) / 2);
  return {
    x: Math.max(-maxX, Math.min(maxX, x)),
    y: Math.max(-maxY, Math.min(maxY, y)),
  };
}
function contrastValue() {
  const shared =
    ["blink", "side", "swipe"].includes($("mode").value) &&
    state.manifest?.display?.shared === true;
  $("stretch").disabled = shared;
  return shared ? 1 : Number($("stretch").value);
}
function drawCursor() {
  if (!state.cursorPoint) return;
  const { x, y } = state.cursorPoint;
  ctx.save();
  ctx.strokeStyle = "#65e2dd";
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x - 7, y);
  ctx.lineTo(x + 7, y);
  ctx.moveTo(x, y - 7);
  ctx.lineTo(x, y + 7);
  ctx.stroke();
  ctx.restore();
}
function draw() {
  const r = canvas.getBoundingClientRect();
  ctx.clearRect(0, 0, r.width, r.height);
  const t = geometry();
  transform = t;
  if (!t) return;
  ctx.imageSmoothingEnabled = $("interpolation")?.value === "smooth";
  const contrast = contrastValue();
  const mode = $("mode").value;
  if (mode === "mosaic") {
    const mosaicView = $("mosaic-view")?.value || "layer62_log";
    let src = "/static/hips_layer62_log.png";
    let label1 = "SPHEREx HiPS Mosaic Cube · Layer 62 (3.3 µm) · Order 5 Npix 445";
    let label2 = "512 × 512 spatial grid · Log / Inferno · Single-layer visualization (Sec 6.2)";
    if (mosaicView === "layer62_viridis") {
      src = "/static/hips_layer62_viridis.png";
      label2 = "512 × 512 spatial grid · Log / Viridis · Single-layer visualization (Sec 6.2)";
    } else if (mosaicView === "median_inferno") {
      src = "/static/hips_cube_median_inferno.png";
      label1 = "SPHEREx HiPS Mosaic Cube · Wavelength Median · Order 5 Npix 445";
      label2 = "512 × 512 spatial grid · Log / Inferno · Wavelength-median stack (Sec 6.3)";
    }

    // Render neighbor tiles surrounding the central field
    ctx.filter = `contrast(${contrast})`;
    for (const [ipix, tile] of state.hipsTileImages.entries()) {
      if (tile.img?.complete && tile.meta?.center && state.manifest?.geometry) {
        const pt = skyToPixel(tile.meta.center[0], tile.meta.center[1]);
        if (pt) {
          const tw = t.width, th = t.height;
          ctx.drawImage(tile.img, pt.x - tw / 2, pt.y - th / 2, tw, th);
          ctx.strokeStyle = "rgba(255, 123, 0, 0.25)";
          ctx.strokeRect(pt.x - tw / 2, pt.y - th / 2, tw, th);
        }
      }
    }

    const img = new Image();
    img.src = src;
    const renderCenter = () => {
      ctx.imageSmoothingEnabled = $("interpolation")?.value === "smooth";
      ctx.filter = `contrast(${contrast})`;
      ctx.drawImage(img, t.x, t.y, t.width, t.height);
      ctx.filter = "none";
      ctx.strokeStyle = "#ff7b00";
      ctx.lineWidth = 1;
      ctx.strokeRect(t.x, t.y, t.width, t.height);
      ctx.fillStyle = "#ffdd80";
      ctx.font = "11px system-ui";
      ctx.fillText(label1, 12, 24);
      ctx.fillText(label2, 12, 40);
      ctx.fillText("Mosaic product · Continuous HiPS sky exploration · Spectral combination does not improve angular resolution", 12, 56);
      
      // Draw target highlight on mosaic
      if (state.showTarget && state.targetPos) {
        const pt = skyToPixel(state.targetPos.ra, state.targetPos.dec);
        if (pt) {
          ctx.save();
          const sqSize = 24;
          ctx.strokeStyle = "#ff4d4d";
          ctx.lineWidth = 1.2;
          ctx.strokeRect(pt.x - sqSize / 2, pt.y - sqSize / 2, sqSize, sqSize);
          ctx.beginPath();
          ctx.moveTo(pt.x - 4, pt.y);
          ctx.lineTo(pt.x + 4, pt.y);
          ctx.moveTo(pt.x, pt.y - 4);
          ctx.lineTo(pt.x, pt.y + 4);
          ctx.stroke();
          ctx.fillStyle = "#ffffff";
          ctx.font = "bold 10px Inter, system-ui, sans-serif";
          const lbl = state.targetName || `ICRS ${state.targetPos.ra.toFixed(4)}°, ${state.targetPos.dec.toFixed(4)}°`;
          ctx.fillText(lbl, pt.x + sqSize / 2 + 5, pt.y + 3);
          ctx.restore();
        }
      }
    };
    img.onload = renderCenter;
    if (img.complete) renderCenter();
    return;
  }
  // Render surrounding HiPS mosaic tiles in the background so sky is visible
  if (state.showHips && state.hipsTileImages.size > 0 && state.manifest?.geometry) {
    ctx.save();
    ctx.filter = `contrast(${contrast}) brightness(0.65)`;
    for (const [ipix, tile] of state.hipsTileImages.entries()) {
      if (tile.img?.complete && tile.meta?.center) {
        const pt = skyToPixel(tile.meta.center[0], tile.meta.center[1]);
        if (pt) {
          // A HEALPix order 5 tile spans ~1.83 deg (~110 arcmin). On our TAN grid (6.2"/pixel):
          const tilePixels = (1.83 * 60 * 60) / 6.2;
          const tw = tilePixels * t.scale, th = tilePixels * t.scale;
          ctx.drawImage(tile.img, pt.x - tw / 2, pt.y - th / 2, tw, th);
          ctx.strokeStyle = "rgba(101, 226, 221, 0.2)";
          ctx.lineWidth = 1;
          ctx.strokeRect(pt.x - tw / 2, pt.y - th / 2, tw, th);
        }
      }
    }
    ctx.restore();
  }

  const a = state.images.get(state.index),
    b = state.images.get(state.b);
  ctx.filter = `contrast(${contrast})`;
  const paint = (image, x, y, w, h) => {
    if (image) ctx.drawImage(image, x, y, w, h);
  };
  if (mode === "side") {
    const g = state.manifest.geometry;
    const scale =
      state.viewMode === "native"
        ? 1
        : Math.min((r.width / 2 - 24) / g.width, (r.height - 48) / g.height) *
          state.zoom;
    const w = g.width * scale,
      h = g.height * scale;
    const y = (r.height - h) / 2 + state.panY;
    paint(a, (r.width / 2 - w) / 2 + state.panX, y, w, h);
    paint(b, r.width / 2 + (r.width / 2 - w) / 2 + state.panX, y, w, h);
  } else {
    paint(a, t.x, t.y, t.width, t.height);
    if (mode === "swipe" && b) {
      ctx.save();
      ctx.beginPath();
      ctx.rect(
        (r.width * Number($("swipe").value)) / 100,
        0,
        r.width,
        r.height,
      );
      ctx.clip();
      paint(b, t.x, t.y, t.width, t.height);
      ctx.restore();
    }
  }
  ctx.filter = "none";
  ctx.strokeStyle = "#B9A5FF";
  ctx.lineWidth = 1.5;
  if (mode !== "side") {
    ctx.strokeRect(t.x, t.y, t.width, t.height);
    // Footprint label
    ctx.fillStyle = "rgba(185, 165, 255, 0.9)";
    ctx.font = "9px Inter, system-ui, sans-serif";
    ctx.fillText("Dated Exposure Footprint", t.x + 4, t.y - 4);
  }
  if (mode !== "single") {
    ctx.fillStyle = "#dbe5f5";
    ctx.font = "10px system-ui";
    ctx.fillText(
      `A: ${state.manifest.frames[state.index]?.date || "—"}`,
      12,
      45,
    );
    ctx.fillText(`B: ${state.manifest.frames[state.b]?.date || "—"}`, 12, 61);
  }
  if (mode === "side") {
    drawCursor();
    return;
  }
  const marks = state.marks.filter((m) => m.frame === state.index);
  for (const p of marks) {
    const pt = skyToPixel(p.ra, p.dec);
    if (pt) circle(pt.x, pt.y, 7, "#8eb8ff");
  }
  if (state.selected) {
    const p = skyToPixel(state.selected.ra, state.selected.dec);
    if (p) circle(p.x, p.y, 10, "#fff");
  }
  if ($("gaia-visible").checked)
    for (const s of state.gaia) {
      const p = skyToPixel(Number(s.ra), Number(s.dec));
      if (p) circle(p.x, p.y, 4, "#d6ba7f");
    }

  if ($("wise-visible").checked)
    for (const source of state.wise) {
      if (source.ra == null || source.dec == null) continue;
      const ra = Number(source.ra), dec = Number(source.dec);
      if (!Number.isFinite(ra) || !Number.isFinite(dec)) continue;
      const p = skyToPixel(ra, dec);
      if (p) {
        ctx.save();
        ctx.strokeStyle = "#65e2dd";
        ctx.lineWidth = 1.5;
        ctx.strokeRect(p.x - 5, p.y - 5, 10, 10);
        ctx.restore();
      }
    }
  // Draw Searched Target highlight (thin red square with center crosshair)
  if (state.showTarget && state.targetPos) {
    const pt = skyToPixel(state.targetPos.ra, state.targetPos.dec);
    if (pt) {
      ctx.save();
      const sqSize = 24; // 24x24 px square
      ctx.strokeStyle = "#ff4d4d"; // High-visibility red
      ctx.lineWidth = 1.2;
      ctx.strokeRect(pt.x - sqSize / 2, pt.y - sqSize / 2, sqSize, sqSize);
      
      // Center crosshair
      ctx.beginPath();
      ctx.moveTo(pt.x - 4, pt.y);
      ctx.lineTo(pt.x + 4, pt.y);
      ctx.moveTo(pt.x, pt.y - 4);
      ctx.lineTo(pt.x, pt.y + 4);
      ctx.stroke();

      // Compact label with target name / resolved coordinates
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 10px Inter, system-ui, sans-serif";
      const lbl = state.targetName || `ICRS ${state.targetPos.ra.toFixed(4)}°, ${state.targetPos.dec.toFixed(4)}°`;
      ctx.fillText(lbl, pt.x + sqSize / 2 + 5, pt.y + 3);
      ctx.restore();
    }
  }
  drawCursor();
}
function circle(x, y, r, color) {
  ctx.beginPath();
  ctx.arc(x, y, r, 0, Math.PI * 2);
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.3;
  ctx.stroke();
}
// Exact gnomonic mapping for the server's fixed TAN grid, with zero-based pixel-center convention.
function pixelToSky(x, y) {
  const t = transform,
    g = state.manifest?.geometry;
  if (!t || !g || g.mode === "native") return null;
  const px = (x - t.x) / t.scale - 0.5,
    py = g.height - 0.5 - (y - t.y) / t.scale;
  if (px < -0.5 || px > g.width - 0.5 || py < -0.5 || py > g.height - 0.5)
    return null;
  const rad = Math.PI / 180;
  const xi = (px + 1 - g.crpix[0]) * g.cdelt[0] * rad,
    eta = (py + 1 - g.crpix[1]) * g.cdelt[1] * rad;
  const a = g.crval[0] * rad,
    d = g.crval[1] * rad,
    den = Math.cos(d) - eta * Math.sin(d);
  return {
    ra: ((a + Math.atan2(xi, den)) / rad + 360) % 360,
    dec: Math.atan2(Math.sin(d) + eta * Math.cos(d), Math.hypot(den, xi)) / rad,
  };
}
function skyToPixel(ra, dec) {
  const t = transform,
    g = state.manifest?.geometry;
  if (!t || !g || g.mode === "native") return null;
  const rad = Math.PI / 180,
    a = (ra - g.crval[0]) * rad,
    d = dec * rad,
    d0 = g.crval[1] * rad;
  const den =
    Math.sin(d0) * Math.sin(d) + Math.cos(d0) * Math.cos(d) * Math.cos(a);
  if (den <= 0) return null;
  const xi = (Math.cos(d) * Math.sin(a)) / den / rad,
    eta =
      (Math.cos(d0) * Math.sin(d) - Math.sin(d0) * Math.cos(d) * Math.cos(a)) /
      den /
      rad;
  const px = xi / g.cdelt[0] + g.crpix[0] - 1,
    py = eta / g.cdelt[1] + g.crpix[1] - 1;
  return {
    x: t.x + (px + 0.5) * t.scale,
    y: t.y + (g.height - 0.5 - py) * t.scale,
  };
}
canvas.onpointerdown = (e) => {
  if (!state.manifest?.frames.length) return;
  if (e.button !== 0) return;
  const r = canvas.getBoundingClientRect();
  const x = e.clientX - r.left,
    y = e.clientY - r.top;
  if (state.tool === "mark") {
    if (state.manifest.geometry.mode === "native") {
      toast(
        "Native detector mode has no validated celestial mapping. Sky marking is unavailable for this raw product.",
      );
      return;
    }
    if ($("mode").value === "side") {
      toast("Use single frame or swipe to mark in the fixed sky grid.");
      return;
    }
    const p = pixelToSky(x, y);
    if (p) {
      state.selected = p;
      state.editing = null;
      $("selected-point").textContent =
        `ICRS ${p.ra.toFixed(7)}°, ${p.dec.toFixed(7)}° · frame ${state.index + 1}`;
      openPanel("evidence");
      draw();
    }
    return;
  }
  drag = { x: e.clientX, y: e.clientY, px: state.panX, py: state.panY };
  canvas.setPointerCapture(e.pointerId);
};
canvas.onpointermove = (e) => {
  const r = canvas.getBoundingClientRect();
  if (drag) {
    const pan = constrainPan(
      drag.px + e.clientX - drag.x,
      drag.py + e.clientY - drag.y,
    );
    state.panX = pan.x;
    state.panY = pan.y;
  }
  state.cursorPoint = { x: e.clientX - r.left, y: e.clientY - r.top };
  if (state.manifest?.geometry.mode === "native") {
    const x = Math.floor((e.clientX - r.left - transform.x) / transform.scale);
    const y = Math.floor(
      state.manifest.geometry.height -
        (e.clientY - r.top - transform.y) / transform.scale,
    );
    $("cursor").textContent =
      x >= 0 &&
      y >= 0 &&
      x < state.manifest.geometry.width &&
      y < state.manifest.geometry.height
        ? `Detector pixel ${x}, ${y} · no sky registration`
        : "Move over the loaded detector image";
    draw();
    return;
  }
  if ($("mode").value === "side") {
    $("cursor").textContent =
      "Use single or swipe view for sky-coordinate readout";
    draw();
    return;
  }
  const p = pixelToSky(e.clientX - r.left, e.clientY - r.top);
  $("cursor").textContent = p
    ? `ICRS ${p.ra.toFixed(6)}°, ${p.dec.toFixed(6)}°`
    : "Move over the loaded image for sky coordinates";
  draw();
};
canvas.onpointerleave = () => {
  if (drag) return;
  state.cursorPoint = null;
  $("cursor").textContent = "Move over the loaded image for coordinates";
  draw();
};
canvas.onpointerup = canvas.onpointercancel = () => (drag = null);
canvas.onlostpointercapture = () => (drag = null);
function zoom(f) {
  if (!state.manifest?.frames.length) return;
  if (state.viewMode === "native") {
    const r = canvas.getBoundingClientRect(),
      g = state.manifest.geometry;
    state.zoom = 1 / (Math.min(r.width / g.width, r.height / g.height) * 0.96);
  }
  state.viewMode = "custom";
  state.zoom = Math.max(0.5, Math.min(12, state.zoom * f));
  const pan = constrainPan(state.panX, state.panY);
  state.panX = pan.x;
  state.panY = pan.y;
  draw();
}
canvas.addEventListener(
  "wheel",
  (e) => {
    e.preventDefault();
    zoom(e.deltaY < 0 ? 1.1 : 1 / 1.1);
  },
  { passive: false },
);
$("zoom-in").onclick = () => zoom(1.25);
$("zoom-out").onclick = () => zoom(0.8);
$("reset").onclick = () => {
  state.zoom = 1;
  state.viewMode = "fit";
  state.panX = state.panY = 0;
  $("stretch").value = 1;
  draw();
};
$("fit-image").onclick = () => {
  state.viewMode = "fit";
  state.zoom = 1;
  state.panX = state.panY = 0;
  draw();
};
if ($("return-target")) {
  $("return-target").onclick = () => {
    state.panX = state.panY = 0;
    state.zoom = 1;
    state.viewMode = "fit";
    draw();
    status("Returned view to searched target");
  };
}
if ($("toggle-target")) {
  $("toggle-target").onchange = (e) => {
    state.showTarget = e.target.checked;
    draw();
  };
}
if ($("toggle-hips")) {
  $("toggle-hips").onchange = (e) => {
    state.showHips = e.target.checked;
    draw();
  };
}
$("native-pixels").onclick = () => {
  if (!state.manifest?.frames.length) return;
  state.viewMode = "native";
  state.panX = state.panY = 0;
  draw();
};
for (const tool of ["pan", "mark"])
  $(tool).onclick = () => {
    state.tool = tool;
    for (const t of ["pan", "mark"])
      $(t).classList.toggle("selected", t === tool);
  };
$("fullscreen").onclick = () => {
  if (document.fullscreenElement) document.exitFullscreen();
  else $("sky").requestFullscreen();
};
$("previous").onclick = () => {
  stop();
  frame(state.index - 1).catch(safeError);
};
$("next").onclick = () => {
  stop();
  frame(state.index + 1).catch(safeError);
};
$("timeline").oninput = () => {
  stop();
  frame(Number($("timeline").value)).catch(safeError);
};
async function tick() {
  if (!state.playing) return;
  const n = state.manifest?.frames.length || 0;
  if (n < 2) {
    stop();
    return;
  }
  let next;
  if ($("mode").value === "blink")
    next = state.index === state.b ? state.blinkA || 0 : state.b;
  else next = state.index + 1;
  if (next >= n) {
    if (!$("loop").checked) {
      stop();
      return;
    }
    next = 0;
  }
  await frame(next);
  if (state.playing)
    state.timer = setTimeout(
      () => tick().catch(safeError),
      Number($("speed").value),
    );
}
$("play").onclick = () => {
  if (state.playing) stop();
  else if ((state.manifest?.frames.length || 0) > 1) {
    state.playing = true;
    $("play").textContent = "Ⅱ";
    state.timer = setTimeout(
      () => tick().catch(safeError),
      Number($("speed").value),
    );
  }
};
$("mode").onchange = () => {
  stop();
  state.blinkA = state.index;
  const pan = constrainPan(state.panX, state.panY);
  state.panX = pan.x;
  state.panY = pan.y;
  frame(state.index).catch(safeError);
};
$("ab").onchange = () => {
  state.b = Number($("ab").value);
  frame(state.index).catch(safeError);
};
$("interpolation").onchange = draw;
$("stretch-fn").onchange = draw;
$("mosaic-view").onchange = draw;
$("stretch").oninput = $("swipe").oninput = draw;
$("contrast-reset").onclick = () => {
  $("stretch").value = 1;
  draw();
};
$("gaia-visible").onchange = draw;
$("wise-visible").onchange = draw;
document.addEventListener("keydown", (e) => {
  if (
    e.target.closest("input,textarea,select,button,dialog") ||
    e.ctrlKey ||
    e.metaKey ||
    e.altKey
  )
    return;
  if (e.key === "ArrowRight") {
    e.preventDefault();
    $("next").click();
  }
  if (e.key === "ArrowLeft") {
    e.preventDefault();
    $("previous").click();
  }
  if (e.code === "Space") {
    e.preventDefault();
    $("play").click();
  }
});
function evidence(f) {
  const root = $("evidence");
  root.replaceChildren();
  const box = document.createElement("div");
  box.className = "evidence-data";
  const dl = document.createElement("dl");
  for (const [key, value] of Object.entries({
    Observed: f.date || "Unknown",
    Mission: f.source,
    Release: f.release,
    Observation: f.id,
    Units: f.units || "Unavailable",
    Wavelength: f.wavelength
      ? `${f.wavelength[0].toFixed(4)} µm · bandwidth ${f.wavelength[1].toFixed(4)} µm · field center`
      : "Not assessed",
    Coverage: `${(f.coverage_fraction * 100).toFixed(1)}%`,
    Alignment: f.alignment,
    Comparison: "Review needed",
  })) {
    const dt = document.createElement("dt"),
      dd = document.createElement("dd");
    dt.textContent = key;
    dd.textContent = value;
    dl.append(dt, dd);
  }
  box.append(dl);
  const footprint = document.createElement("p");
  footprint.className = "tiny";
  footprint.textContent = f.returned_footprint
    ? `Returned archive footprint: ${f.returned_footprint.width_arcmin.toFixed(2)}′ × ${f.returned_footprint.height_arcmin.toFixed(2)}′ (may be rotated). Valid data: ${(f.coverage_fraction * 100).toFixed(1)}% of output grid.`
    : "Returned archive footprint not recorded in this cached processing version. Output WCS extent and valid-data fraction are shown separately; no footprint is invented.";
  box.append(footprint);
  for (const [label, url] of [
    ["Original archive file", f.url],
    ["Download native FITS", f.original.url],
    ["Display-grid FITS", f.aligned.url],
  ]) {
    const a = document.createElement("a");
    a.href = url;
    a.textContent = label;
    a.target = "_blank";
    a.rel = "noopener";
    const p = document.createElement("p");
    p.className = "evidence-link";
    p.append(a);
    box.append(p);
  }
  const warning = document.createElement("p");
  warning.className = "warning";
  warning.textContent =
    state.manifest.geometry.mode === "native"
      ? "Raw detector counts. No celestial registration or calibrated source measurements."
      : "Display comparison only. Alignment residual and filter-response matching have not been measured.";
  box.append(warning);
  const advanced = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Quality flags & processing";
  advanced.append(summary);
  const flags = document.createElement("p");
  flags.className = "tiny";
  flags.textContent =
    "Raw flag values: " + (f.flag_values.join(", ") || "Unavailable");
  advanced.append(flags);
  for (const flag of (f.decoded_flags || []).filter((f) => f.pixels > 0)) {
    const p = document.createElement("p");
    p.className = "tiny";
    p.textContent = `${flag.name}: ${flag.description || flag.category} · ${flag.pixels} pixels`;
    advanced.append(p);
  }
  const method = document.createElement("p");
  method.className = "tiny";
  method.textContent = f.mask_policy + " " + f.variance;
  advanced.append(method);
  box.append(advanced);
  root.append(box);
}
function renderRows() {
  const box = $("observations");
  box.replaceChildren();
  const m = state.manifest;
  if (!m.frames.length) {
    const p = document.createElement("p");
    p.textContent =
      m.discovery.warning ||
      "No usable frames returned. This is not evidence of source absence.";
    box.append(p);
  }
  m.frames.forEach((f, i) => {
    const row = document.createElement("div");
    row.className = "observation-row";
    const b = document.createElement("button");
    b.textContent = i + 1;
    b.onclick = () => frame(i).catch(safeError);
    const text = document.createElement("div");
    text.textContent = f.date || "Unknown date";
    const small = document.createElement("small");
    small.textContent = f.id;
    text.append(small);
    const meta = document.createElement("p");
    meta.className = "observation-meta";
    meta.textContent = `${f.wavelength ? f.wavelength[0].toFixed(4) + " µm · width " + f.wavelength[1].toFixed(4) + " µm" : "Wavelength not assessed"} · valid ${(f.coverage_fraction * 100).toFixed(1)}%`;
    const a = document.createElement("a");
    a.href = f.original.url;
    a.textContent = "FITS ↗";
    row.append(b, text, meta, a);
    box.append(row);
  });
  const recovered = m.discovery?.mode === "cached-native-recovery-v1" || m.discovery?.cached_cutout_recovery;
  if (m.excluded.length || recovered) {
    const notice = document.createElement("div");
    notice.className = "partial-notice";
    const message = document.createElement("p");
    message.textContent = recovered
      ? `${m.frames.length} observations loaded using saved original FITS. Some archive requests failed; coverage may be incomplete.`
      : `${m.frames.length} loaded · ${m.excluded.length} unavailable from archive. Usable frames retained.`;
    notice.append(message);
    const retry = document.createElement("button");
    retry.textContent = recovered ? "Retry live archive search" : "Retry unavailable observations";
    retry.onclick = () => {
      if (!recovered) state.retrySequence = m.id;
      $("search-form").requestSubmit();
    };
    notice.append(retry);
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "Details";
    details.append(summary);
    const failureList = document.createElement("div");
    failureList.className = "failure-details";
    details.append(failureList);
    if (recovered) {
      const provenance = document.createElement("p");
      provenance.textContent = m.discovery.warning;
      failureList.append(provenance);
    }
    for (const item of m.excluded) {
      const p = document.createElement("p");
      p.className = "excluded-row";
      const reason = /503|502|504|500|429/.test(item.reason)
        ? "Archive temporarily unavailable. Retry later."
        : item.reason.split(" for url:")[0].slice(0, 240);
      p.textContent = `${item.id} · ${reason}`;
      failureList.append(p);
    }
    notice.append(details);
    $("partial-summary").replaceChildren(notice);
    $("partial-summary").hidden = false;
  } else {
    $("partial-summary").replaceChildren();
    $("partial-summary").hidden = true;
  }
}
async function refreshMarks() {
  if (!state.manifest) return;
  const r = await api(
    "/api/v1/candidates?sequence=" + state.manifest.id,
    undefined,
    "GET",
  );
  state.marks = r.candidates;
  const box = $("marks");
  box.replaceChildren();
  for (const mark of state.marks) {
    const div = document.createElement("div");
    div.className = "mark-card";
    const p = document.createElement("p");
    p.textContent = `Frame ${mark.frame + 1} · ${mark.classification} · ${mark.note}`;
    div.append(p);
    for (const [label, fn] of [
      [
        "Edit",
        () => {
          state.selected = { ra: mark.ra, dec: mark.dec };
          state.editing = mark;
          $("classification").value = mark.classification;
          $("note").value = mark.note;
          frame(mark.frame);
          $("selected-point").textContent =
            `Editing ${mark.id.slice(0, 8)} · revision ${mark.revision}`;
        },
      ],
      [
        "Delete",
        async () => {
          await api("/api/v1/candidates/" + mark.id, {}, "DELETE");
          await refreshMarks();
          draw();
        },
      ],
    ]) {
      const b = document.createElement("button");
      b.textContent = label;
      b.onclick = () => Promise.resolve(fn()).catch(safeError);
      div.append(b);
    }
    box.append(div);
  }
  draw();
}
if ($("clear-marks")) {
  $("clear-marks").onclick = async () => {
    if (!state.marks.length) {
      toast("No annotations to clear.");
      return;
    }
    try {
      for (const m of state.marks) {
        await api("/api/v1/candidates/" + m.id, {}, "DELETE");
      }
      state.selected = null;
      state.editing = null;
      await refreshMarks();
      toast("All annotations removed.");
    } catch (e) {
      safeError(e);
    }
  };
}
$("save-mark").onclick = async () => {
  if (!state.selected || !state.manifest) {
    toast("Mark a source in a loaded frame first.");
    return;
  }
  try {
    const old = state.editing;
    await api(
      "/api/v1/candidates" + (old ? "/" + old.id : ""),
      {
        sequence: state.manifest.id,
        frame: state.index,
        ...state.selected,
        classification: $("classification").value,
        note: $("note").value,
        revision: old?.revision,
      },
      old ? "PATCH" : "POST",
    );
    state.editing = null;
    await refreshMarks();
    toast("Annotation saved to your private session.");
  } catch (e) {
    safeError(e);
  }
};
$("gaia").onclick = async () => {
  if (!state.manifest) {
    toast("Load a field first.");
    return;
  }
  if (state.manifest.geometry.mode === "native") {
    toast(
      "Gaia overlay requires validated celestial WCS; this is native detector mode.",
    );
    return;
  }
  const b = $("gaia");
  b.disabled = true;
  try {
    const controller = new AbortController();
    const gen = state.generation;
    const job = await api("/api/v1/catalogs/gaia", state.manifest.selection);
    const r = await waitJob(job, gen, controller.signal);
    state.gaia = r.sources;
    $("gaia-result").textContent =
      `${r.sources.length} Gaia DR3 sources · J2016.0 · gold circles · positions not propagated.`;
    draw();
  } catch (e) {
    safeError(e);
  } finally {
    b.disabled = false;
    state.job = null;
  }
};
$("save-report").onclick = async () => {
  if (!state.manifest) {
    toast("Load observations first.");
    return;
  }
  try {
    const r = await api("/api/v1/reports", {
      sequence: state.manifest.id,
      title: $("report-title").value,
      parent: state.parentReport,
      settings: {
        index: state.index,
        b: state.b,
        mode: $("mode").value,
        zoom: state.zoom,
        panX: state.panX,
        panY: state.panY,
        contrast: $("stretch").value,
        viewMode: state.viewMode,
        interpolation: $("interpolation").value,
        stretchFunction: $("stretch-fn").value,
        mosaicView: $("mosaic-view").value,
        selected: state.selected,
      },
    });
    state.parentReport = r.id;
    toast(
      "Immutable evidence report saved. Open Investigations to export or share.",
    );
  } catch (e) {
    safeError(e);
  }
};
$("state-link").onclick = async () => {
  const params = new URLSearchParams(selection());
  params.set("frame", state.index);
  params.set("b", state.b);
  params.set("mode", $("mode").value);
  params.set("zoom", state.zoom);
  params.set("viewMode", state.viewMode);
  params.set("contrast", $("stretch").value);
  params.set("panX", state.panX);
  params.set("panY", state.panY);
  if (state.manifest) params.set("sequence", state.manifest.id);
  const url = location.origin + "/?" + params;
  try {
    await navigator.clipboard.writeText(url);
    history.replaceState(null, "", url);
    toast(
      state.manifest
        ? "View link copied. It will reopen this saved field and its display state."
        : "View settings copied. Load observations before sharing a field.",
    );
  } catch (e) {
    safeError(e);
  }
};
const params = new URLSearchParams(location.search);
for (const k of [
  "source",
  "unit",
  "ra",
  "dec",
  "width",
  "height",
  "release",
  "detector",
  "start",
  "end",
])
  if (params.has(k)) $(k).value = params.get(k);
if (params.has("ra"))
  $("identity").textContent =
    "Coordinates restored from link. Validate and load explicitly.";
$("wise").onclick = async () => {
  if (!state.manifest || state.manifest.geometry.mode === "native") {
    toast("AllWISE overlay requires a loaded field with validated celestial WCS.");
    return;
  }
  const button = $("wise"), manifest = state.manifest, generation = state.generation;
  button.disabled = true;
  $("wise-result").textContent = "Querying AllWISE…";
  try {
    const job = await api("/api/v1/catalogs/wise", manifest.selection);
    const result = await waitJob(job, generation, new AbortController().signal);
    if (manifest !== state.manifest || generation !== state.generation) return;
    state.wise = result.sources;
    $("wise-result").textContent = `${result.sources.length} AllWISE sources · cyan squares${result.possibly_truncated ? " · 200-source limit reached" : ""}. ${result.warning}`;
    draw();
  } catch (error) {
    if (manifest === state.manifest) $("wise-result").textContent = error.message;
  } finally {
    button.disabled = false;
    state.job = null;
  }
};
window.argusTest = { pixelToSky, skyToPixel, geometry, state };
import "./analysis.js";

if (params.has("sequence")) {
  busy(true);
  api("/api/v1/sequences/" + params.get("sequence"), undefined, "GET")
    .then(async (manifest) => {
      if (params.has("parent")) {
        const report = await api("/api/v1/reports/" + params.get("parent"), undefined, "GET");
        const saved = report.settings || {};
        for (const [key, value] of Object.entries(saved))
          if (value !== null && typeof value !== "object")
            params.set(key === "index" ? "frame" : key, String(value));
        $("report-title").value = report.title || "";
        for (const [key, id] of [["interpolation", "interpolation"], ["stretchFunction", "stretch-fn"], ["mosaicView", "mosaic-view"]])
          if (saved[key]) $(id).value = saved[key];
        await loadManifest(manifest);
        state.selected = saved.selected || null;
        updateAnalysisContext();
        draw();
      } else {
      await loadManifest(manifest);
      }
      $("identity").textContent =
        "Saved field restored from view link. Verify the recorded provenance before interpreting it.";
    })
    .catch((error) => {
      // A view link can outlive its local cache.  Preserve its requested
      // coordinates/settings, but do not silently present an empty viewer as
      // though the saved observation had loaded.
      state.manifest = null;
      $("identity").textContent =
        "Saved field is no longer available here. Coordinates and display settings were restored; load observations to create new evidence.";
      status("Saved view unavailable; no observations loaded");
      toast("Saved field unavailable. Coordinates were restored; load observations to continue.");
      console.warn("Unable to restore saved view link:", error);
    })
    .finally(() => busy(false));
}

$("source").addEventListener("change", () => {
  const native = $("source").value === "neossat";
  $("release").disabled = $("detector").disabled = native;
  $("identity").textContent = native
    ? "NEOSSat optical raw products. FOV selects archive coverage, not a calibrated sky crop."
    : "SPHEREx near infrared. Resolve a reference position or enter explicit coordinates.";
});
