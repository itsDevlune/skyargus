import { $ } from "./common.js";

export function createCubeViewer(getCube, sample) {
  const canvas = $("cube-canvas"),
    ctx = canvas.getContext("2d");
  const state = {
    zoom: 1,
    x: 0,
    y: 0,
    native: false,
    tool: "pan",
    a: null,
    b: null,
    phase: false,
    playing: false,
    version: 0,
  };
  const cache = new Map();
  let playbackVersion = 0;
  const visible = () => !document.hidden && !$("workspace-panel").hidden && !$("analysis-content").hidden && $("real-cube-workbench").open;
  let drag = null,
    blink = null,
    timer = null;
  const clearBlink = () => {
    clearTimeout(blink);
    blink = null;
  };
  function geometry(side = false) {
    const r = canvas.getBoundingClientRect(),
      vw = side ? r.width / 2 : r.width,
      base = Math.min((vw - 16) / 512, (r.height - 16) / 512);
    const scale = state.native ? state.zoom : base * state.zoom;
    return { vw, w: 512 * scale, h: 512 * scale, height: r.height, scale };
  }
  function constrain() {
    const g = geometry($("cube-mode").value === "side");
    state.x = Math.max(
      -Math.max(0, (g.w - g.vw) / 2),
      Math.min(Math.max(0, (g.w - g.vw) / 2), state.x),
    );
    state.y = Math.max(
      -Math.max(0, (g.h - g.height) / 2),
      Math.min(Math.max(0, (g.h - g.height) / 2), state.y),
    );
  }
  function draw() {
    const r = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, r.width, r.height);
    if (!state.a) return;
    const mode = $("cube-mode").value,
      g = geometry(mode === "side");
    ctx.imageSmoothingEnabled = $("cube-interpolation").value === 'smooth';
    ctx.filter = `contrast(${$("cube-contrast").value})`;
    const image = (img, offset = 0) => {
      if (img)
        ctx.drawImage(
          img,
          offset + (g.vw - g.w) / 2 + state.x,
          (g.height - g.h) / 2 + state.y,
          g.w,
          g.h,
        );
    };
    if (mode === "side") {
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, g.vw, r.height);
      ctx.clip();
      image(state.a);
      ctx.restore();
      ctx.save();
      ctx.beginPath();
      ctx.rect(g.vw, 0, g.vw, r.height);
      ctx.clip();
      image(state.b, g.vw);
      ctx.restore();
    } else if (mode === "swipe") {
      image(state.a);
      ctx.save();
      ctx.beginPath();
      ctx.rect(0, 0, (r.width * Number($("cube-swipe").value)) / 100, r.height);
      ctx.clip();
      image(state.b);
      ctx.restore();
    } else image(mode === "blink" && state.phase ? state.b : state.a);
    const cube = getCube(),
      a = cube?.channels[Number($("cube-channel").value)],
      b = cube?.channels[Number($("cube-b").value)];
    $("cube-view-label").textContent = a
      ? `A ${a.index + 1}: ${a.wavelength_um.toFixed(3)} µm${a.available ? "" : " · no coverage"}${mode !== "single" && b ? ` | B ${b.index + 1}: ${b.wavelength_um.toFixed(3)} µm${b.available ? "" : " · no coverage"}` : ""}${mode === "blink" ? ` · showing ${state.phase ? "B" : "A"}` : ""}`
      : "";
  }
  function resize() {
    const r = canvas.getBoundingClientRect(),
      dpr = devicePixelRatio || 1;
    if (r.width <= 0 || r.height <= 0) return;
    canvas.width = Math.round(r.width * dpr);
    canvas.height = Math.round(r.height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    constrain();
    draw();
  }
  new ResizeObserver(resize).observe($("cube-stage"));
  async function image(url) {
    if (cache.has(url)) {
      const value = cache.get(url);
      cache.delete(url);
      cache.set(url, value);
      return value;
    }
    const img = new Image();
    img.src = url;
    const pending = img.decode().then(() => img);
    cache.set(url, pending);
    while (cache.size > 6) cache.delete(cache.keys().next().value);
    try { return await pending; } catch (error) { if (cache.get(url) === pending) cache.delete(url); throw error; }
  }
  async function refresh() {
    const cube = getCube();
    if (!cube) return;
    const version = ++state.version;
    clearBlink();
    const a = Number($("cube-channel").value),
      b = Number($("cube-b").value),
      compare = $("cube-mode").value !== "single",
      coverage = $("cube-hits").checked ? 1 : 0;
    const url = (i, ref) =>
      `/api/v1/cubes/${cube.cube_id}/planes/${i}?coverage=${coverage}${compare ? `&reference=${ref}` : ""}`;
    state.a = state.b = null;
    $("cube-view-label").textContent = 'Loading channel images…';
    draw();
    $("cube-a").value = a;
    try {
      const [ia, ib] = await Promise.all([
        image(url(a, b)),
        compare ? image(url(b, a)) : Promise.resolve(null),
      ]);
      if (version !== state.version) return;
      state.a = ia;
      state.b = ib;
      if (!visible()) return;
      constrain();
      draw();
      if ($("cube-mode").value === "blink") tickBlink();
    } catch (e) {
      if (version === state.version)
        $("cube-view-label").textContent =
          `Channel image unavailable: ${e.message}`;
    }
  }
  function tickBlink() {
    clearBlink();
    if (!visible()) return;
    blink = setTimeout(
      () => {
        if (!visible()) return;
        state.phase = !state.phase;
        draw();
        if ($("cube-mode").value === "blink" && !$("workspace-panel").hidden)
          tickBlink();
      },
      Number($("cube-speed").value),
    );
  }
  function stop() {
    playbackVersion++;
    clearTimeout(timer);
    timer = null;
    state.playing = false;
    $("cube-play").textContent = "Play wavelengths";
    $("cube-play").setAttribute("aria-pressed", "false");
  }
  async function step(delta) {
    const current = Number($("cube-channel").value);
    let next = current + delta;
    if (next > 101 || next < 0) {
      if (!$("cube-loop").checked) {
        stop();
        return;
      }
      next = (next + 102) % 102;
    }
    $("cube-channel").value = next;
    $("cube-channel").dispatchEvent(new Event("input"));
    await refresh();
  }
  function tick(version = playbackVersion) {
    timer = setTimeout(
      async () => {
        if (!state.playing || version !== playbackVersion || !visible()) return;
        await step(1);
        if (state.playing && version === playbackVersion) tick(version);
      },
      Number($("cube-speed").value),
    );
  }
  $("cube-play").onclick = () => {
    if (state.playing) {
      stop();
      return;
    }
    if (!getCube()) return;
    state.playing = true;
    playbackVersion++;
    $("cube-play").textContent = "Pause wavelengths";
    $("cube-play").setAttribute("aria-pressed", "true");
    tick();
  };
  $("cube-previous").onclick = () => step(-1);
  $("cube-next").onclick = () => step(1);
  $("cube-a").onchange = () => {
    $("cube-channel").value = $("cube-a").value;
    $("cube-channel").dispatchEvent(new Event("input"));
  };
  $("cube-b").onchange = $("cube-mode").onchange = refresh;
  $("cube-swipe").oninput = draw;
  $("cube-contrast").oninput = draw;
  $("cube-interpolation").onchange = draw;
  $("cube-contrast-reset").onclick = () => { $("cube-contrast").value=1; draw(); };
  $("cube-speed").onchange = () => {
    if (state.playing) {
      playbackVersion++;
      clearTimeout(timer);
      tick();
    }
    if ($("cube-mode").value === "blink" && state.a) tickBlink();
  };
  function zoom(factor) {
    state.zoom = Math.max(0.25, Math.min(16, state.zoom * factor));
    constrain();
    draw();
  }
  $("cube-plus").onclick = () => zoom(1.4);
  $("cube-minus").onclick = () => zoom(1 / 1.4);
  $("cube-fit").onclick = $("cube-reset").onclick = () => {
    state.zoom = 1;
    state.native = false;
    state.x = state.y = 0;
    draw();
  };
  $("cube-native").onclick = () => {
    state.native = true;
    state.zoom = 1;
    constrain();
    draw();
  };
  for (const tool of ["pan", "sample"])
    $("cube-" + tool).onclick = () => {
      state.tool = tool;
      for (const name of ["pan", "sample"])
        $("cube-" + name).setAttribute("aria-pressed", String(name === tool));
    };
  canvas.onpointerdown = (e) => {
    if (e.button !== 0 || !state.a) return;
    const r = canvas.getBoundingClientRect(),
      side = $("cube-mode").value === "side",
      g = geometry(side),
      offset = side && e.clientX - r.left >= g.vw ? g.vw : 0;
    if (state.tool === "sample") {
      const x = Math.floor(
          (e.clientX - r.left - offset - (g.vw - g.w) / 2 - state.x) / g.scale,
        ),
        y =
          511 -
          Math.floor(
            (e.clientY - r.top - (g.height - g.h) / 2 - state.y) / g.scale,
          );
      if (x >= 0 && x < 512 && y >= 0 && y < 512) sample(x, y);
      return;
    }
    drag = { x: e.clientX, y: e.clientY, px: state.x, py: state.y };
    canvas.setPointerCapture(e.pointerId);
  };
  canvas.onpointermove = (e) => {
    if (!drag) return;
    state.x = drag.px + e.clientX - drag.x;
    state.y = drag.py + e.clientY - drag.y;
    constrain();
    draw();
  };
  canvas.onpointerup =
    canvas.onpointercancel =
    canvas.onlostpointercapture =
      () => {
        drag = null;
      };
  canvas.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      zoom(e.deltaY < 0 ? 1.15 : 1 / 1.15);
    },
    { passive: false },
  );
  canvas.onkeydown = (e) => {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      e.stopPropagation();
      step(e.key === "ArrowRight" ? 1 : -1);
    }
  };
  $("cube-fullscreen").onclick = () => {
    const stage = $("cube-stage");
    (document.fullscreenElement
      ? document.exitFullscreen()
      : stage.requestFullscreen()
    ).catch((e) => {
      $("cube-view-label").textContent = e.message;
    });
  };
  const exitFullscreen = () => document.exitFullscreen().catch(error => {
    $("cube-view-label").textContent = error.message;
  });
  if ($("cube-exit-fullscreen")) $("cube-exit-fullscreen").onclick = exitFullscreen;
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && document.fullscreenElement === $("cube-stage")) {
      event.preventDefault();
      event.stopImmediatePropagation();
      exitFullscreen();
    }
  }, true);
  new MutationObserver(() => {
    if ($("workspace-panel").hidden) {
      stop();
      clearBlink();
    } else if (visible() && state.a && $("cube-mode").value === 'blink') tickBlink();
  }).observe($("workspace-panel"), {
    attributes: true,
    attributeFilter: ["hidden"],
  });
  new MutationObserver(() => {
    if ($("analysis-content").hidden) { stop(); clearBlink(); }
    else if (visible() && state.a && $("cube-mode").value === 'blink') tickBlink();
  }).observe($("analysis-content"), {attributes:true, attributeFilter:['hidden']});
  $("real-cube-workbench").addEventListener("toggle", () => {
    if (!$("real-cube-workbench").open) {
      stop();
      clearBlink();
    } else refresh();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stop();
      clearBlink();
    }
  });
  return {
    refresh,
    reset() {
      stop();
      clearBlink();
      cache.clear();
      state.zoom = 1;
      state.x = state.y = 0;
      state.native = false;
      for (const id of ["cube-a", "cube-b"]) {
        $(id).replaceChildren();
        for (const c of getCube().channels) {
          const option = document.createElement("option");
          option.value = c.index;
          option.textContent = `${c.index + 1} · ${c.wavelength_um.toFixed(3)} µm${c.available ? "" : " · unavailable"}`;
          $(id).append(option);
        }
      }
      $("cube-b").value = "1";
    },
    state,
  };
}
