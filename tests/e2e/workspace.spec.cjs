const { test, expect } = require("@playwright/test");

async function loadComparisonFixture(page, { shared = false } = {}) {
  const frames = ["2025-01-01", "2025-02-01"].map((date, index) => ({
    id: `comparison-frame-${index}`,
    date,
    source: "SPHEREx",
    release: "DR1",
    units: "MJy / sr",
    wavelength: null,
    coverage_fraction: 1,
    flag_values: [],
    decoded_flags: [],
    alignment: "WCS aligned",
    mask_policy: "Uncovered pixels are blank.",
    variance: "Display only.",
    url: `https://example.invalid/comparison-frame-${index}.fits`,
    original: { url: `/comparison-frame-${index}.fits` },
    aligned: { url: `/comparison-aligned-${index}.fits` },
    preview: { url: `/comparison-preview-${index}.svg` },
  }));
  await page.route("**/api/v1/sequences/comparison-test", (route) =>
    route.fulfill({
      json: {
        id: "comparison-test",
        selection: {
          ra: 10,
          dec: 20,
          source: "spherex",
          unit: "deg",
          width: 6,
          height: 6,
          release: "dr1",
          detector: 3,
        },
        frames,
        excluded: [],
        discovery: {},
        geometry: {
          mode: "celestial",
          width: 200,
          height: 100,
          crval: [10, 20],
          crpix: [100.5, 50.5],
          cdelt: [-0.0017, 0.0017],
        },
        display: { shared, low: 0, high: 1 },
      },
    }),
  );
  await page.route("**/api/v1/candidates?sequence=comparison-test", (route) =>
    route.fulfill({ json: { candidates: [] } }),
  );
  await page.route("**/comparison-preview-*.svg", (route) => {
    const color = route.request().url().includes("preview-0")
      ? "#18202a"
      : "#283018";
    return route.fulfill({
      contentType: "image/svg+xml",
      body: `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><rect width="200" height="100" fill="${color}"/></svg>`,
    });
  });
  await page.goto("/?sequence=comparison-test");
  await page.waitForFunction(() => window.argusTest?.state.images.has(0));
}

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/hips/cube*", (route) =>
    route.fulfill({ json: {} }),
  );
});

test("responsive accessible shell has no fake sky or javascript errors", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "A field of possibilities." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open quick start" }).click();
  await expect(page.locator("#help-dialog")).toBeVisible();
  await page.locator("#help-dialog button").click();
  await page
    .getByRole("button", { name: "Switch light and dark theme" })
    .click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});
test("explicit invalid coordinates do not enqueue archive work", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator("#request-details > summary").click();
  await page.locator("#ra").fill("360");
  await page.getByRole("button", { name: "Load observations" }).click();
  await expect(page.locator("#status")).toContainText("RA must");
});

test("FOV presets set square full dimensions and custom fields remain rectangular", async ({
  page,
}) => {
  await page.goto("/");
  await page.locator("#request-details > summary").click();
  for (const value of ["3", "6", "12"]) {
    await page.locator(`#fov-presets button[data-fov="${value}"]`).click();
    await expect(page.locator("#width")).toHaveValue(value);
    await expect(page.locator("#height")).toHaveValue(value);
  }
  await page.locator("#width").fill("7.5");
  await page.locator("#height").fill("12.5");
  await expect(page.locator("#width")).toHaveValue("7.5");
  await expect(page.locator("#height")).toHaveValue("12.5");
  await expect(page.getByLabel("Field width arcminutes")).toBeVisible();
  await expect(page.getByLabel("Field height arcminutes")).toBeVisible();
});

test("timeline playback advances, pauses, loops, stops, and labels dated frames", async ({
  page,
}) => {
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jI9sAAAAASUVORK5CYII=",
    "base64",
  );
  const frames = ["2025-01-01", "2025-02-01", "2025-03-01"].map(
    (date, index) => ({
      id: `frame-${index}`,
      date,
      source: "SPHEREx",
      release: "DR1",
      units: "MJy / sr",
      wavelength: null,
      coverage_fraction: 1,
      flag_values: [],
      decoded_flags: [],
      alignment: "WCS aligned",
      mask_policy: "Uncovered pixels are blank.",
      variance: "Display only.",
      url: `https://example.invalid/frame-${index}.fits`,
      original: { url: `/original-${index}.fits` },
      aligned: { url: `/aligned-${index}.fits` },
      preview: { url: `/preview-${index}.png` },
    }),
  );
  await page.route("**/api/v1/sequences/playback-test", (route) =>
    route.fulfill({
      json: {
        id: "playback-test",
        selection: { ra: 10, dec: 20, source: "spherex", release: "dr1" },
        frames,
        excluded: [],
        discovery: {},
        geometry: {
          mode: "celestial",
          width: 1,
          height: 1,
          crval: [10, 20],
          crpix: [1, 1],
          cdelt: [-0.001, 0.001],
        },
      },
    }),
  );
  await page.route("**/api/v1/candidates?sequence=playback-test", (route) =>
    route.fulfill({ json: { candidates: [] } }),
  );
  await page.route("**/preview-*.png", (route) =>
    route.fulfill({ contentType: "image/png", body: png }),
  );
  await page.goto("/?sequence=playback-test");

  await expect(page.locator("#count")).toHaveText("1 / 3");
  await expect(page.locator("#first-date")).toHaveText("2025-01-01");
  await expect(page.locator("#last-date")).toHaveText("2025-03-01");
  await expect(page.locator("#frame-summary")).toContainText("2025-01-01");
  await page.locator("#next").click();
  await expect(page.locator("#count")).toHaveText("2 / 3");
  await page.locator("#previous").click();
  await expect(page.locator("#count")).toHaveText("1 / 3");

  await page.locator("#speed").selectOption("600");
  await page.locator("#play").click();
  await expect(page.locator("#count")).toHaveText("2 / 3", { timeout: 2000 });
  await page.locator("#play").click();
  await page.waitForTimeout(700);
  await expect(page.locator("#count")).toHaveText("2 / 3");

  await page.locator("#timeline").fill("2");
  await page.locator("#play").click();
  await expect(page.locator("#count")).toHaveText("1 / 3", { timeout: 2000 });
  await page.locator("#loop").uncheck();
  await page.locator("#timeline").fill("2");
  await page.locator("#play").click();
  await page.waitForTimeout(800);
  await expect(page.locator("#count")).toHaveText("3 / 3");
  await expect(page.locator("#play")).toHaveText("▶");
});

test("A/B blink alternates between the selected observations", async ({
  page,
}) => {
  await loadComparisonFixture(page);
  await page.locator("#ab").selectOption("1");
  await page.locator("#mode").selectOption("blink");
  await page.locator("#speed").selectOption("600");
  await page.locator("#play").click();
  await expect(page.locator("#count")).toHaveText("2 / 2", { timeout: 2000 });
  await expect(page.locator("#count")).toHaveText("1 / 2", { timeout: 2000 });
  await page.locator("#play").click();
});

test("side-by-side comparison preserves each preview's aspect ratio", async ({
  page,
}) => {
  await loadComparisonFixture(page);
  await page.evaluate(() => {
    const context = document.querySelector("#viewer").getContext("2d");
    window.comparisonDraws = [];
    const drawImage = context.drawImage.bind(context);
    context.drawImage = (image, ...args) => {
      window.comparisonDraws.push({
        sourceRatio: image.naturalWidth / image.naturalHeight,
        displayRatio: args[2] / args[3],
      });
      return drawImage(image, ...args);
    };
  });
  await page.locator("#mode").selectOption("side");
  await page.waitForFunction(() => window.comparisonDraws.length >= 2);
  const draws = await page.evaluate(() => window.comparisonDraws.slice(-2));
  expect(draws).toHaveLength(2);
  for (const draw of draws)
    expect(draw.displayRatio).toBeCloseTo(draw.sourceRatio, 4);
});

test("swipe comparison updates the visible split between observations", async ({
  page,
}) => {
  await loadComparisonFixture(page);
  await page.locator("#mode").selectOption("swipe");
  await page.waitForFunction(() => window.argusTest?.state.images.has(1));
  const before = await page.locator("#viewer").screenshot();
  await page.locator("#swipe").fill("90");
  const after = await page.locator("#viewer").screenshot();
  expect(Buffer.compare(before, after)).not.toBe(0);
});

test("shared stretch disables per-frame contrast and reset remains safe", async ({
  page,
}) => {
  await loadComparisonFixture(page, { shared: true });
  await page.locator("#stretch").fill("1.8");
  await page.locator("#contrast-reset").click();
  await expect(page.locator("#stretch")).toHaveValue("1");
  await page.locator("#stretch").fill("1.8");
  await page.locator("#mode").selectOption("blink");
  await expect(page.locator("#stretch")).toBeDisabled();
  await page.locator("#contrast-reset").click();
  await expect(page.locator("#stretch")).toHaveValue("1");
  await page.locator("#mode").selectOption("single");
  await expect(page.locator("#stretch")).toBeEnabled();
});

test("Gaia overlay toggles and upstream errors remain visible", async ({
  page,
}) => {
  await loadComparisonFixture(page);
  await page.locator("#open-evidence").click();
  await page
    .locator("summary")
    .filter({ hasText: "Reference context" })
    .click();
  await page.route("**/api/v1/catalogs/gaia", (route) =>
    route.fulfill({
      json: { job: "gaia-e2e", status_url: "/api/v1/jobs/gaia-e2e" },
    }),
  );
  await page.route("**/api/v1/jobs/gaia-e2e", (route) =>
    route.fulfill({
      json: {
        state: "completed",
        stage: "Complete",
        result: {
          sources: [{ source_id: "gaia-1", ra: 10, dec: 20 }],
        },
      },
    }),
  );
  await page.locator("#gaia").click();
  await expect(page.locator("#gaia-result")).toContainText(
    "1 Gaia DR3 sources",
  );
  const visible = await page.locator("#viewer").screenshot();
  await page.locator("#gaia-visible").uncheck();
  const hidden = await page.locator("#viewer").screenshot();
  expect(Buffer.compare(visible, hidden)).not.toBe(0);

  await page.route("**/api/v1/catalogs/gaia", (route) =>
    route.fulfill({
      status: 502,
      json: {
        error: {
          code: "resolver_unavailable",
          message: "Gaia DR3 is unavailable right now",
          retryable: true,
        },
      },
    }),
  );
  await page.locator("#gaia").click();
  await expect(page.locator("#status")).toContainText(
    "Gaia DR3 is unavailable right now",
  );
  await expect(page.locator("#gaia")).toBeEnabled();
});

test("pan stays within the loaded image and zoom/FOV changes do not search until requested", async ({
  page,
}) => {
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jI9sAAAAASUVORK5CYII=",
    "base64",
  );
  let searches = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/api/v1/searches")) searches++;
  });
  await page.route("**/api/v1/sequences/pan-test", (route) =>
    route.fulfill({
      json: {
        id: "pan-test",
        selection: { ra: 10, dec: 20, source: "spherex", release: "dr1" },
        frames: [
          {
            id: "frame-0",
            date: "2025-01-01",
            source: "SPHEREx",
            release: "DR1",
            units: "MJy / sr",
            wavelength: null,
            coverage_fraction: 1,
            flag_values: [],
            decoded_flags: [],
            alignment: "WCS aligned",
            mask_policy: "Uncovered pixels are blank.",
            variance: "Display only.",
            url: "https://example.invalid/frame.fits",
            original: { url: "/original.fits" },
            aligned: { url: "/aligned.fits" },
            preview: { url: "/preview-pan.png" },
          },
        ],
        excluded: [],
        discovery: {},
        geometry: {
          mode: "celestial",
          width: 1,
          height: 1,
          crval: [10, 20],
          crpix: [1, 1],
          cdelt: [-0.001, 0.001],
        },
      },
    }),
  );
  await page.route("**/api/v1/candidates?sequence=pan-test", (route) =>
    route.fulfill({ json: { candidates: [] } }),
  );
  await page.route("**/api/v1/searches", (route) =>
    route.fulfill({ status: 400, json: { error: { message: "Search intercepted" } } }),
  );
  await page.route("**/preview-pan.png", (route) =>
    route.fulfill({ contentType: "image/png", body: png }),
  );
  await page.goto("/?sequence=pan-test&zoom=2&panX=999999&panY=-999999");
  await expect(page.locator("#count")).toHaveText("1 / 1");

  const initial = await page.evaluate(() => {
    const g = window.argusTest.geometry();
    const pan = window.argusTest.state;
    return {
      x: g.x,
      y: g.y,
      width: g.width,
      height: g.height,
      cw: g.cw,
      ch: g.ch,
      panX: pan.panX,
      panY: pan.panY,
    };
  });
  expect(initial.panX).toBeLessThanOrEqual(Math.abs(initial.cw - initial.width) / 2);
  expect(initial.panY).toBeGreaterThanOrEqual(-Math.abs(initial.ch - initial.height) / 2);
  expect(initial.x + initial.width).toBeGreaterThan(0);
  expect(initial.y).toBeLessThan(initial.ch);

  const canvas = await page.locator("#viewer").boundingBox();
  await page.locator("#zoom-in").click();
  // A wide responsive viewport can still contain the whole square image
  // after one step. Establish overflow on both axes before testing clamps.
  for (let step = 0; step < 10; step++) {
    const overflow = await page.evaluate(() => {
      const g = window.argusTest.geometry();
      return g.width > g.cw * 1.5 && g.height > g.ch * 1.5;
    });
    if (overflow) break;
    await page.locator("#zoom-in").click();
  }
  await page.mouse.move(canvas.x + canvas.width / 2, canvas.y + canvas.height / 2);
  await page.mouse.down();
  await page.mouse.move(canvas.x + canvas.width * 3, canvas.y + canvas.height * 3);
  await page.mouse.up();
  await page.mouse.wheel(0, -240);
  const afterPan = await page.evaluate(() => {
    const g = window.argusTest.geometry();
    const s = window.argusTest.state;
    return { ...g, panX: s.panX, panY: s.panY };
  });
  expect(afterPan.panX).toBeLessThanOrEqual(
    Math.abs(afterPan.cw - afterPan.width) / 2 + 1,
  );
  expect(afterPan.panY).toBeLessThanOrEqual(
    Math.abs(afterPan.ch - afterPan.height) / 2 + 1,
  );
  expect(afterPan.x).toBeLessThanOrEqual(1);
  expect(afterPan.x + afterPan.width).toBeGreaterThanOrEqual(afterPan.cw - 1);
  await page.locator("#width").fill("8");
  await page.locator("#height").fill("4");
  expect(searches).toBe(0);
  await page.getByRole("button", { name: "Load observations" }).click();
  await expect(page.locator("#status")).toContainText("Search intercepted");
  expect(searches).toBe(1);
});

test("native cursor reports image pixels and crosshair tracks pointer without claiming sky coordinates", async ({
  page,
}) => {
  const png = Buffer.from(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jI9sAAAAASUVORK5CYII=",
    "base64",
  );
  await page.route("**/api/v1/sequences/native-cursor-test", (route) =>
    route.fulfill({
      json: {
        id: "native-cursor-test",
        selection: { ra: 10, dec: 20, source: "neossat", release: "CADC raw" },
        frames: [
          {
            id: "native-frame",
            date: "2025-01-01",
            source: "NEOSSat",
            release: "CADC raw",
            units: "raw ADU",
            wavelength: null,
            coverage_fraction: 1,
            flag_values: [],
            decoded_flags: [],
            alignment: "Native detector; sky orientation not assessed",
            mask_policy: "Native data.",
            variance: "Not calibrated.",
            url: "https://example.invalid/native.fits",
            original: { url: "/native.fits" },
            aligned: { url: "/native-display.fits" },
            preview: { url: "/preview-native.png" },
          },
        ],
        excluded: [],
        discovery: {},
        geometry: { mode: "native", width: 1, height: 1 },
      },
    }),
  );
  await page.route("**/api/v1/candidates?sequence=native-cursor-test", (route) =>
    route.fulfill({ json: { candidates: [] } }),
  );
  await page.route("**/preview-native.png", (route) =>
    route.fulfill({ contentType: "image/png", body: png }),
  );
  await page.goto("/?sequence=native-cursor-test");
  await expect(page.locator("#sky-label")).toContainText("Native detector pixels");
  await expect(page.locator(".orientation")).toBeHidden();
  const canvas = await page.locator("#viewer").boundingBox();
  const x = canvas.x + canvas.width / 2;
  const y = canvas.y + canvas.height / 2;
  await page.mouse.move(x, y);
  await expect(page.locator("#cursor")).toContainText("Detector pixel");
  await expect(page.locator("#cursor")).toContainText("no sky registration");
  const crosshair = await page.evaluate(() => {
    const { x, y } = window.argusTest.state.cursorPoint;
    const canvas = document.querySelector("#viewer");
    const dpr = window.devicePixelRatio || 1;
    return {
      x,
      y,
      color: canvas
        .getContext("2d")
        .getImageData(Math.round((x - 6) * dpr), Math.round(y * dpr), 1, 1).data,
    };
  });
  expect(crosshair.x).toBeGreaterThan(0);
  expect(crosshair.y).toBeGreaterThan(0);
  expect(crosshair.color[2]).toBeGreaterThan(crosshair.color[0]);
});
test("source methods disclose limits and required agency notice", async ({
  page,
}) => {
  await page.goto("/sources/");
  await expect(
    page.getByRole("heading", { name: "Required agency notice" }),
  ).toBeVisible();
  await expect(page.locator("blockquote")).toContainText(
    "NASA does not endorse",
  );
});

test("five target presets resolve live coordinates and failed lookup clears stale values", async ({
  page,
}) => {
  const names = [
    "Barnard's Star",
    "Epsilon Indi B",
    "WISE J085510.83-071442.5",
    "RW Aur",
    "R Dra",
  ];
  await page.route("**/api/v1/resolve", async (route) => {
    const { name } = route.request().postDataJSON();
    if (name === "R Dra") {
      await route.fulfill({ status: 502, json: { error: { message: "Resolver unavailable" } } });
      return;
    }
    await route.fulfill({
      json: {
        name: `Canonical ${name}`,
        ra: 123.456,
        dec: -45.678,
        resolver: "test fixture",
        epoch: "J2000 reference; proper motion not applied",
      },
    });
  });
  await page.goto("/");
  await page.locator("#request-details > summary").click();
  await page.locator("#request-details .examples > summary").click();
  await expect(page.locator("#targets button[data-name]")).toHaveCount(5);
  for (const name of names.slice(0, 4)) {
    await page.locator(`#targets button[data-name="${name}"]`).click();
    await expect(page.locator("#object")).toHaveValue(name);
    await expect(page.locator("#ra")).toHaveValue("123.45600000");
    await expect(page.locator("#dec")).toHaveValue("-45.67800000");
    await expect(page.locator("#identity")).toContainText(`Canonical ${name}`);
    await expect(page.locator("#identity")).toContainText("J2000 reference");
  }
  await page.locator('#targets button[data-name="R Dra"]').click();
  await expect(page.locator("#ra")).toHaveValue("");
  await expect(page.locator("#dec")).toHaveValue("");
  await expect(page.locator("#status")).toContainText("Resolver unavailable");
});

test("an earlier lookup cannot overwrite a newer target", async ({ page }) => {
  let releaseFirst;
  const delayFirst = new Promise((resolve) => { releaseFirst = resolve; });
  await page.route("**/api/v1/resolve", async (route) => {
    const { name } = route.request().postDataJSON();
    if (name === "RW Aur") await delayFirst;
    await route.fulfill({ json: { name, ra: 10, dec: 20, resolver: "fixture", epoch: "reference" } });
  });
  await page.goto("/");
  await page.locator("#request-details > summary").click();
  await page.locator("#request-details .examples > summary").click();
  const first = page.waitForRequest("**/api/v1/resolve");
  await page.locator('[data-name="RW Aur"]').click();
  await first;
  await page.locator('[data-name="R Dra"]').click();
  await expect(page.locator("#identity")).toContainText("R Dra");
  const finished = page.waitForEvent("requestfinished", (r) => r.url().endsWith("/api/v1/resolve"));
  releaseFirst();
  await finished;
  await page.evaluate(() => new Promise(requestAnimationFrame));
  await expect(page.locator("#identity")).toContainText("R Dra");
});

test("difference analysis discloses nominal overlap and unassessed response calibration", async ({ page }) => {
  await page.route("**/api/v1/analyses", (route) =>
    route.fulfill({
      status: 202,
      json: { job: "response-contract-job", status_url: "/api/v1/jobs/response-contract-job" },
    }),
  );
  await page.route("**/api/v1/jobs/response-contract-job", (route) =>
    route.fulfill({
      json: {
        state: "completed",
        stage: "Difference complete",
        result: {
          valid_pixel_count: 100,
          total_pixels: 200,
          residual_min: -1,
          residual_max: 1,
          bandpass_comparison: {
            status: "overlapping_display_bandpasses",
            reason: "Field-center display lookup only",
          },
          response_comparability: "not_assessed",
          warning: "Calibrated spectral response and PSF matching are not assessed.",
        },
      },
    }),
  );
  await loadComparisonFixture(page);
  await page.locator("#open-analysis").click();
  await page.locator("#analysis-tool").selectOption("difference");
  await page.locator("#compute-difference").click();

  const result = page.locator("#difference-result");
  await expect(result).toContainText("Bandpass: overlapping_display_bandpasses");
  await expect(result).toContainText("Response: not_assessed");
  await expect(result).toContainText("Calibrated spectral response and PSF matching are not assessed.");
});
