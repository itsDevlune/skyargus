const { test, expect } = require("@playwright/test");

test("UX-03 & UX-04: responsive layout, keyboard stepping, bounded playback memory, and pointer interaction", async ({
  page,
  request,
}) => {
  const cachedSequence = await request.get(
    "/api/v1/sequences/3122bdf8-1727-44ff-ad8c-aac23cffe151",
  );
  test.skip(
    cachedSequence.status() !== 200,
    "Local real cache not installed",
  );
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/?sequence=3122bdf8-1727-44ff-ad8c-aac23cffe151");
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);

  // 1. Keyboard frame stepping (UX-03)
  const initialFrame = await page.evaluate(() => window.argusTest.state.index);
  await page.keyboard.press("ArrowRight");
  await page.waitForTimeout(300);
  const nextFrame = await page.evaluate(() => window.argusTest.state.index);
  expect(nextFrame).toBe(initialFrame + 1);

  await page.keyboard.press("ArrowLeft");
  await page.waitForTimeout(300);
  const prevFrame = await page.evaluate(() => window.argusTest.state.index);
  expect(prevFrame).toBe(initialFrame);

  // 2. Pointer drag / pan interaction (UX-04)
  // Fit deliberately centers the full image; zoom beyond both viewport axes
  // before verifying unconstrained positive pointer displacement.
  for (let step = 0; step < 12; step++)
    await page.locator("#zoom-in").click();
  const sky = await page.locator("#viewer").boundingBox();
  await page.mouse.move(sky.x + 100, sky.y + 100);
  await page.mouse.down();
  await page.mouse.move(sky.x + 160, sky.y + 160);
  await page.mouse.up();
  const pan = await page.evaluate(() => [
    window.argusTest.state.panX,
    window.argusTest.state.panY,
  ]);
  expect(pan[0]).toBeGreaterThan(0);
  expect(pan[1]).toBeGreaterThan(0);

  // 3. Memory-bounded caching (UX-04: max 3 images in map)
  const imageCount = await page.evaluate(
    () => window.argusTest.state.images.size,
  );
  expect(imageCount).toBeLessThanOrEqual(3);
});

test("RS-02: Gaia DR3 catalog query and overlay rendering", async ({
  page,
  request,
}) => {
  const cachedSequence = await request.get(
    "/api/v1/sequences/3122bdf8-1727-44ff-ad8c-aac23cffe151",
  );
  test.skip(
    cachedSequence.status() !== 200,
    "Local real cache not installed",
  );
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/?sequence=3122bdf8-1727-44ff-ad8c-aac23cffe151");
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);

  await page.route("**/api/v1/catalogs/gaia", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        job: "gaia-test-e2e-job",
        status_url: "/api/v1/jobs/gaia-test-e2e-job",
      }),
    });
  });

  await page.route("**/api/v1/jobs/gaia-test-e2e-job", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "gaia-test-e2e-job",
        state: "completed",
        stage: "Gaia DR3 query complete",
        result: {
          release: "Gaia DR3",
          sources: [
            {
              source_id: "4472832130942575872",
              ra: 269.452075,
              dec: 4.693391,
              phot_g_mean_mag: 9.5,
            },
          ],
        },
      }),
    });
  });

  await page.locator("#open-evidence").click();
  await page.locator("#evidence-panel details:has(#gaia) summary").click();
  await page.locator("#gaia").click();
  await page.waitForTimeout(600);

  await expect(page.locator("#gaia-result")).toContainText(
    "1 Gaia DR3 sources · J2016.0",
  );
  const gaiaCount = await page.evaluate(
    () => window.argusTest.state.gaia.length,
  );
  expect(gaiaCount).toBe(1);
});

test("RS-05, RS-06, RS-07, RS-08: NEOSSat workspace, provenance and agency notices", async ({
  page,
}) => {
  // Check Sources & terms page
  await page.goto("/sources/");
  await expect(page.locator("body")).toContainText("CADC NEOSSat");
  await expect(page.locator("body")).toContainText("Canadian Space Agency");
  await expect(page.locator("body")).toContainText("Required agency notice");

  // Check Explorer NEOSSat source selection
  await page.goto("/");
  await page.locator("#source").selectOption("neossat");
  await expect(page.locator("#release")).toBeDisabled();
  await expect(page.locator("#detector")).toBeDisabled();
  await expect(page.locator("#identity")).toContainText(
    "NEOSSat optical raw products",
  );
});
