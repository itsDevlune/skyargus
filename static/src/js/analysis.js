import { $, api, toast, download } from "./common.js";
import { renderCoverage, spectrumPlot } from './spectral-workbench.js';
import './cube-explorer.js';

const panel = document.createElement("section");
panel.className = "analysis-panel";

panel.innerHTML = `
<div id="tool-motion-panel">
  <div class="section-label">CHANGE LAB / MANUAL APPARENT MOTION</div>
  <h3>Measure a marked trail</h3>
  <p class="tiny">Mark the same candidate in two or more dated frames. This estimates angular motion from your associations; it does not establish an orbit or identity.</p>
  <label for="position-error">Assumed error per position (arcsec)</label>
  <input id="position-error" type="number" min="0.01" max="60" value="3.1" step="0.1">
  <button id="fit-motion">Request motion fit</button>
  <div id="motion-result" aria-live="polite"></div>
</div>

<div id="tool-spectrum-panel" hidden>
  <div class="section-label">CHANGE LAB / SOURCE SPECTRUM</div>
  <h3>On-the-fly quick-look spectrum</h3>
  <p class="tiny">Extracts aperture photometry across dated exposures at the selected mark or field center with local background subtraction and variance propagation.</p>
  <div class="two">
    <div>
      <label for="spec-ra">RA (deg)</label>
      <input id="spec-ra" type="number" step="0.000001">
    </div>
    <div>
      <label for="spec-dec">Dec (deg)</label>
      <input id="spec-dec" type="number" step="0.000001">
    </div>
  </div>
  <label for="spec-aperture">Aperture radius (pixels)</label>
  <input id="spec-aperture" type="number" min="1" max="10" value="3" step="0.5">
  <button id="extract-spectrum">Extract spectrum</button>
  <div id="spectrum-result" aria-live="polite"></div>
</div>

<div id="tool-difference-panel" hidden>
  <div class="section-label">CHANGE LAB / IMAGE SUBTRACTION</div>
  <h3>Subtract two dated epochs</h3>
  <p class="tiny">Computes (Frame B - Frame A) on the common celestial grid with zero-centered residual stretch and variance propagation.</p>
  <div class="two">
    <div>
      <label for="diff-frame-a">Frame A (Reference)</label>
      <select id="diff-frame-a"></select>
    </div>
    <div>
      <label for="diff-frame-b">Frame B (Target)</label>
      <select id="diff-frame-b"></select>
    </div>
  </div>
  <button id="compute-difference">Compute difference</button>
  <div id="difference-result" aria-live="polite"></div>
</div>

<div id="tool-stack-panel" hidden>
  <div class="section-label">CHANGE LAB / EPOCH STACKING</div>
  <h3>Quality-masked weighted stack</h3>
  <p class="tiny">Inverse-variance weighted combination of compatible observations within the selected epoch window, excluding documented quality flags.</p>
  <div id="stack-frame-checkboxes" class="checkbox-list"></div>
  <button id="compute-stack">Stack selected frames</button>
  <div id="stack-result" aria-live="polite"></div>
</div>

<div id="tool-composite-panel" hidden>
  <div class="section-label">CHANGE LAB / SPECTRAL COMPOSITE</div>
  <h3>False-colour RGB composite</h3>
  <p class="tiny">Assign three different SPHEREx wavelength bands to Red, Green, and Blue channels to visualize infrared spectral slopes.</p>
  <div class="three">
    <div>
      <label for="comp-red">Red channel</label>
      <select id="comp-red"></select>
    </div>
    <div>
      <label for="comp-green">Green channel</label>
      <select id="comp-green"></select>
    </div>
    <div>
      <label for="comp-blue">Blue channel</label>
      <select id="comp-blue"></select>
    </div>
  </div>
  <button id="compute-composite">Generate RGB composite</button>
  <div id="composite-result" aria-live="polite"></div>
</div>
`;

document.getElementById("analysis-content").append(panel);

// Populate analysis options
const toolSelect = $("analysis-tool");
if (!toolSelect.querySelector("option[value='composite']")) {
  const opt = document.createElement("option");
  opt.value = "composite";
  opt.textContent = "RGB Spectral Composite";
  toolSelect.append(opt);
}

function updateFrameSelectors() {
  const manifest = window.argusTest?.state?.manifest;
  if (!manifest || !manifest.frames) return;
  const frames = manifest.frames;
  renderCoverage(manifest);

  const populate = (sel) => {
    sel.replaceChildren();
    frames.forEach((f, idx) => {
      const opt = document.createElement("option");
      opt.value = idx;
      const wl = f.wavelength ? `${f.wavelength[0].toFixed(3)} µm` : `det ${f.detector}`;
      opt.textContent = `Frame ${idx + 1} (${f.date ? f.date.slice(0, 10) : "unknown"}, ${wl})`;
      sel.append(opt);
    });
  };

  populate($("diff-frame-a"));
  populate($("diff-frame-b"));
  if (frames.length > 1) $("diff-frame-b").value = 1;

  populate($("comp-red"));
  populate($("comp-green"));
  populate($("comp-blue"));
  if (frames.length >= 3) {
    $("comp-red").value = 1;
    $("comp-green").value = 2;
    $("comp-blue").value = 0;
  }

  const stackBox = $("stack-frame-checkboxes");
  stackBox.replaceChildren();
  frames.forEach((f, idx) => {
    const lbl = document.createElement("label");
    lbl.className = "inline";
    const chk = document.createElement("input");
    chk.type = "checkbox";
    chk.value = idx;
    chk.checked = true;
    const wl = f.wavelength ? `${f.wavelength[0].toFixed(3)} µm` : `det ${f.detector}`;
    lbl.append(chk, ` Frame ${idx + 1} (${f.date ? f.date.slice(0, 10) : ""}, ${wl})`);
    stackBox.append(lbl);
  });

  if (window.argusTest?.state?.selected) {
    $("spec-ra").value = window.argusTest.state.selected.ra.toFixed(6);
    $("spec-dec").value = window.argusTest.state.selected.dec.toFixed(6);
  } else if (manifest.selection) {
    $("spec-ra").value = manifest.selection.ra.toFixed(6);
    $("spec-dec").value = manifest.selection.dec.toFixed(6);
  }
}

toolSelect.onchange = () => {
  const method = toolSelect.value;
  const isNative = window.argusTest?.state?.manifest?.geometry?.mode === "native";

  $("tool-motion-panel").hidden = method !== "motion" || isNative;
  $("tool-spectrum-panel").hidden = method !== "spectrum" || isNative;
  $("tool-difference-panel").hidden = method !== "difference" || isNative;
  $("tool-stack-panel").hidden = method !== "stack" || isNative;
  $("tool-composite-panel").hidden = method !== "composite" || isNative;

  if (isNative) {
    $("analysis-unavailable").hidden = false;
    $("analysis-unavailable").textContent = "Quantitative celestial analyses are unavailable for unreprojected raw detector imagery.";
  } else {
    $("analysis-unavailable").hidden = true;
  }
  updateFrameSelectors();
};

document.getElementById("open-analysis").addEventListener("click", () => {
  updateFrameSelectors();
});

// Helper for polling job
async function pollAnalysisJob(jobId, statusUrl, resultElement, label) {
  resultElement.textContent = `Queueing ${label}...`;
  for (let i = 0; i < 300; i++) {
    const j = await api(statusUrl, undefined, "GET");
    resultElement.textContent = j.stage || "Processing...";
    if (j.state === "completed") {
      return j.result;
    }
    if (["failed", "cancelled"].includes(j.state)) {
      throw Error(j.error?.message || j.state);
    }
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw Error(`${label} request timed out.`);
}

// 1. Motion Fit
$("fit-motion").onclick = async () => {
  const state = window.argusTest.state;
  if (!state.manifest) {
    toast("Load a sequence and save at least two marks first.");
    return;
  }
  const button = $("fit-motion");
  button.disabled = true;
  try {
    const job = await api("/api/v1/analyses", {
      method: "motion",
      sequence: state.manifest.id,
      position_error_arcsec: Number($("position-error").value),
    });
    const result = await pollAnalysisJob(job.job, job.status_url, $("motion-result"), "motion fit");
    const box = $("motion-result");
    box.replaceChildren();
    const p = document.createElement("p");
    p.className = "warning";
    p.textContent = `East ${result.east_arcsec_day.toFixed(3)}; north ${result.north_arcsec_day.toFixed(3)} arcsec/day. Assumed component uncertainty ±${result.component_error_arcsec_day.toFixed(3)} arcsec/day. Baseline ${result.baseline_days.toFixed(5)} days. RMS ${result.rms_arcsec.toFixed(3)} arcsec. ${result.warning}`;
    box.append(p);
    const exp = document.createElement("button");
    exp.textContent = "Export motion JSON";
    exp.onclick = () => download("argus-manual-motion.json", result);
    box.append(exp);
    const points = document.createElement("ol");
    for (const point of result.points) {
      const li = document.createElement("li");
      li.textContent = `${point.date} · ${point.ra.toFixed(7)}°, ${point.dec.toFixed(7)}° · frame ${point.frame + 1}`;
      points.append(li);
    }
    box.append(points);
  } catch (e) {
    toast(e.message);
    $("motion-result").textContent = e.message;
  } finally {
    button.disabled = false;
  }
};

// 2. Spectrum Extraction
$("extract-spectrum").onclick = async () => {
  const state = window.argusTest.state;
  if (!state.manifest) {
    toast("Load a sequence first.");
    return;
  }
  const button = $("extract-spectrum");
  button.disabled = true;
  try {
    const job = await api("/api/v1/analyses", {
      method: "spectrum",
      sequence: state.manifest.id,
      ra: Number($("spec-ra").value),
      dec: Number($("spec-dec").value),
      aperture_radius_pix: Number($("spec-aperture").value),
    });
    const result = await pollAnalysisJob(job.job, job.status_url, $("spectrum-result"), "spectrum");
    const box = $("spectrum-result");
    box.replaceChildren();

    const p = document.createElement("p");
    p.className = "tiny";
    p.textContent = `${result.measurement_count} spectral points extracted. Method: ${result.method}. ${result.warning}`;
    box.append(p);

    const exp = document.createElement("button");
    exp.textContent = "Export Spectrum JSON";
    exp.onclick = () => download("argus-spectrum.json", result);
    box.append(exp);
    box.append(spectrumPlot(result));

    const tbl = document.createElement("table");
    tbl.className = "spectral-table tiny";
    tbl.innerHTML = `
      <thead>
        <tr><th>λ (µm)</th><th>Flux (mJy)</th><th>±</th><th>AB mag</th><th>Flags</th></tr>
      </thead>
      <tbody></tbody>
    `;
    const tbody = tbl.querySelector("tbody");
    result.measurements.forEach((m) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${m.wavelength_um.toFixed(3)}</td>
        <td>${m.flux_mjy.toFixed(2)}</td>
        <td>${m.flux_err_mjy ? m.flux_err_mjy.toFixed(2) : "—"}</td>
        <td>${m.abmag ? m.abmag.toFixed(2) : "—"}</td>
        <td>${m.bad_pixel_count > 0 ? `<span class="badge caution">${m.bad_pixel_count} bad</span>` : "ok"}</td>
      `;
      tbody.append(tr);
    });
    box.append(tbl);
  } catch (e) {
    toast(e.message);
    $("spectrum-result").textContent = e.message;
  } finally {
    button.disabled = false;
  }
};

// 3. Image Subtraction
$("compute-difference").onclick = async () => {
  const state = window.argusTest.state;
  if (!state.manifest) {
    toast("Load a sequence first.");
    return;
  }
  const button = $("compute-difference");
  button.disabled = true;
  try {
    const fa = Number($("diff-frame-a").value);
    const fb = Number($("diff-frame-b").value);
    const job = await api("/api/v1/analyses", {
      method: "difference",
      sequence: state.manifest.id,
      frame_a: fa,
      frame_b: fb,
    });
    const result = await pollAnalysisJob(job.job, job.status_url, $("difference-result"), "difference");
    const box = $("difference-result");
    box.replaceChildren();

    const p = document.createElement("p");
    p.className = "warning";
    p.textContent = `Difference (Frame ${fb + 1} - Frame ${fa + 1}). Valid pixels: ${result.valid_pixel_count}/${result.total_pixels}. Residual range: [${result.residual_min.toFixed(2)}, ${result.residual_max.toFixed(2)}] MJy/sr. Bandpass: ${result.bandpass_comparison.status}. Response: ${result.response_comparability}. ${result.warning}`;
    box.append(p);

    if (result.preview) {
      const img = document.createElement("img");
      img.src = result.preview.url;
      img.alt = "Difference preview";
      img.className = "analysis-preview";
      box.append(img);
    }
  } catch (e) {
    toast(e.message);
    $("difference-result").textContent = e.message;
  } finally {
    button.disabled = false;
  }
};

// 4. Stacking
$("compute-stack").onclick = async () => {
  const state = window.argusTest.state;
  if (!state.manifest) {
    toast("Load a sequence first.");
    return;
  }
  const button = $("compute-stack");
  button.disabled = true;
  try {
    const checked = Array.from($("stack-frame-checkboxes").querySelectorAll("input:checked")).map((c) => Number(c.value));
    if (checked.length === 0) {
      throw Error("Select at least one frame to stack.");
    }
    const job = await api("/api/v1/analyses", {
      method: "stack",
      sequence: state.manifest.id,
      frames: checked,
    });
    const result = await pollAnalysisJob(job.job, job.status_url, $("stack-result"), "stack");
    const box = $("stack-result");
    box.replaceChildren();

    const p = document.createElement("p");
    p.className = "warning";
    p.textContent = `Stacked ${result.contributor_count} frames. Hits per pixel: ${result.hits_min}–${result.hits_max}. Surface brightness: [${result.flux_min.toFixed(2)}, ${result.flux_max.toFixed(2)}] MJy/sr. ${result.method}. ${result.warning}`;
    box.append(p);

    if (result.preview) {
      const img = document.createElement("img");
      img.src = result.preview.url;
      img.alt = "Stacked epoch preview";
      img.className = "analysis-preview";
      box.append(img);
    }
    if (result.fits) {
      const a = document.createElement("a");
      a.href = result.fits.url;
      a.download = `argus-epoch-stack-${state.manifest.id}.fits`;
      a.className = "button";
      a.textContent = "Download Stacked FITS";
      box.append(a);
    }
  } catch (e) {
    toast(e.message);
    $("stack-result").textContent = e.message;
  } finally {
    button.disabled = false;
  }
};

// 5. RGB Composite
$("compute-composite").onclick = async () => {
  const state = window.argusTest.state;
  if (!state.manifest) {
    toast("Load a sequence first.");
    return;
  }
  const button = $("compute-composite");
  button.disabled = true;
  try {
    const r = Number($("comp-red").value);
    const g = Number($("comp-green").value);
    const b = Number($("comp-blue").value);
    const job = await api("/api/v1/analyses", {
      method: "composite",
      sequence: state.manifest.id,
      red: r,
      green: g,
      blue: b,
    });
    const result = await pollAnalysisJob(job.job, job.status_url, $("composite-result"), "RGB composite");
    const box = $("composite-result");
    box.replaceChildren();

    const p = document.createElement("p");
    p.className = "warning";
    const m = result.mapping;
    p.textContent = `RGB composite: R=Frame ${r + 1} (${m.red.wavelength ? m.red.wavelength[0].toFixed(3) + " µm" : ""}), G=Frame ${g + 1} (${m.green.wavelength ? m.green.wavelength[0].toFixed(3) + " µm" : ""}), B=Frame ${b + 1} (${m.blue.wavelength ? m.blue.wavelength[0].toFixed(3) + " µm" : ""}). ${result.method}. ${result.warning}`;
    box.append(p);

    if (result.preview) {
      const img = document.createElement("img");
      img.src = result.preview.url;
      img.alt = "False-colour RGB preview";
      img.className = "analysis-preview";
      box.append(img);
    }
  } catch (e) {
    toast(e.message);
    $("composite-result").textContent = e.message;
  } finally {
    button.disabled = false;
  }
};
