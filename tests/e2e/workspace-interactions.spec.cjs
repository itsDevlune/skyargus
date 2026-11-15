const { test, expect } = require("@playwright/test");
test("search sends resolved field, request failures preserve data, playback and drag work", async ({
  page,
  request,
}) => {
  const id = "93924ac9-a107-4bb6-8f92-e0aee7b106a3";
  test.skip(
    (await request.get("/api/v1/sequences/" + id)).status() !== 200,
    "Real cache unavailable",
  );
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/?sequence=" + id);
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
  await page.locator("#object").fill("Barnard's Star");
  let submitted;
  await page.route("**/api/v1/resolve", (r) =>
    r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        name: "Barnard's Star",
        ra: 269.452075,
        dec: 4.693391,
        resolver: "Controlled resolver test response",
        epoch: "Reference coordinates; proper motion not applied.",
      }),
    }),
  );
  page.on("request", (r) => {
    if (r.url().endsWith("/api/v1/searches")) submitted = r.postDataJSON();
  });
  const searchResponse = page.waitForResponse((r) =>
    r.url().endsWith("/api/v1/searches"),
  );
  await page.locator("button.load").click();
  const actualSearch = await (await searchResponse).json();
  expect(actualSearch.cached).toBe(true);
  expect(actualSearch.sequence).toBe(id);
  await expect(page.locator("#identity")).toContainText(
    "proper motion not applied",
  );
  expect(Number(submitted.ra)).toBeCloseTo(269.452075, 7);
  expect(Number(submitted.width)).toBe(6);
  await expect(page.locator("button.load")).toBeEnabled();
  await expect(page.locator("#next")).toBeEnabled();
  await page.locator("#next").click();
  await page.waitForFunction(() => window.argusTest.state.index === 1);
  await page.locator("#previous").click();
  await page.waitForFunction(() => window.argusTest.state.index === 0);
  await page.locator("#play").click();
  await page.waitForFunction(() => window.argusTest.state.index > 0);
  await page.locator("#play").click();
  expect(await page.evaluate(() => window.argusTest.state.playing)).toBe(false);
  await page.locator("#zoom-in").click();
  // Enlarge beyond the viewport on both axes before asserting free pan.
  // One step leaves a square cutout narrower than this wide viewport.
  for (let step = 0; step < 11; step++)
    await page.locator("#zoom-in").click();
  const b = await page.locator("#viewer").boundingBox();
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
  await page.mouse.down();
  await page.mouse.move(b.x + b.width / 2 + 40, b.y + b.height / 2 + 25);
  await page.mouse.up();
  expect(await page.evaluate(() => window.argusTest.state.panX)).toBe(40);
  await page.locator("#reset").click();
  expect(
    await page.evaluate(() => [
      window.argusTest.state.panX,
      window.argusTest.state.panY,
      window.argusTest.state.zoom,
    ]),
  ).toEqual([0, 0, 1]);
  await page.locator("#width").fill("12");
  await page.locator("#height").fill("12");
  await page.unroute("**/api/v1/searches");
  await page.route("**/api/v1/searches", async (r) => {
    submitted = r.request().postDataJSON();
    await r.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify({
        error: { message: "Controlled archive outage", retryable: true },
      }),
    });
  });
  await page.locator("button.load").click();
  await expect(page.locator("#status")).toContainText(
    "Controlled archive outage",
  );
  expect(Number(submitted.width)).toBe(12);
  expect(Number(submitted.height)).toBe(12);
  expect(
    await page.evaluate(() => window.argusTest.state.manifest.geometry.width),
  ).toBe(58);
  await expect(page.locator("#request-pending")).toBeVisible();
});
