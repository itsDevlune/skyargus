const { test, expect } = require("@playwright/test");
const id = "3122bdf8-1727-44ff-ad8c-aac23cffe151";
for (const [width, height] of [
  [1366, 768],
  [1920, 1080],
  [390, 844],
]) {
  test(`image and playback stay visible at ${width}x${height}`, async ({
    page,
    request,
  }) => {
    test.skip(
      (await request.get("/api/v1/sequences/" + id)).status() !== 200,
      "Local real cache not installed",
    );
    await page.setViewportSize({ width, height });
    await page.goto("/?sequence=" + id);
    await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
    await expect(page.locator("#workspace-panel")).toBeHidden();
    const sky = await page.locator("#viewer").boundingBox(),
      play = await page.locator("#play").boundingBox(),
      timeline = await page.locator(".timeline").boundingBox();
    expect(sky.height).toBeGreaterThan(width > 700 ? 300 : 200);
    expect(play.y + play.height).toBeLessThanOrEqual(height);
    expect(timeline.y + timeline.height).toBeLessThanOrEqual(height);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
  });
}
test("fit/native pixels, pending FOV, panels and annotation state are correct", async ({
  page,
  request,
}) => {
  test.skip(
    (await request.get("/api/v1/sequences/" + id)).status() !== 200,
    "Local real cache not installed",
  );
  await page.goto("/?sequence=" + id);
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
  await expect(page.locator("#geometry-summary")).toContainText("6′ × 6′");
  await page.locator("#width").fill("12");
  await page.locator("#height").fill("12");
  await expect(page.locator("#request-pending")).toBeVisible();
  await expect(page.locator("#geometry-summary")).toContainText("6′ × 6′");
  expect(
    await page.evaluate(() => window.argusTest.state.manifest.geometry.width),
  ).toBe(58);
  await page.locator("#width").fill("6");
  await page.locator("#height").fill("6");
  await page.evaluate(() => {
    const c = document.getElementById("viewer").getContext("2d"),
      original = c.drawImage;
    window.pixelDraws = [];
    c.drawImage = function (...a) {
      window.pixelDraws.push({
        iw: a[0].naturalWidth,
        ih: a[0].naturalHeight,
        w: a[3],
        h: a[4],
      });
      return original.apply(this, a);
    };
  });
  await page.locator("#native-pixels").click();
  const native = await page.evaluate(() => window.pixelDraws.at(-1));
  expect(native.w).toBe(native.iw);
  expect(native.h).toBe(native.ih);
  await page.locator("#fit-image").click();
  expect(await page.evaluate(() => window.argusTest.state.viewMode)).toBe(
    "fit",
  );
  await page.locator("#zoom-in").click();
  await page.locator("#mark").click();
  const b = await page.locator("#viewer").boundingBox();
  await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
  await expect(page.locator("#evidence-panel")).toBeVisible();
  const before = await page.evaluate(() => ({
    selected: window.argusTest.state.selected,
    zoom: window.argusTest.state.zoom,
    panX: window.argusTest.state.panX,
    panY: window.argusTest.state.panY,
  }));
  await page.locator("#close-panel").click();
  await page.locator("#open-observations").click();
  await expect(page.locator("#observations")).toContainText("2025W33");
  await page.locator("#open-analysis").click();
  await expect(page.locator("#analysis-context")).toContainText(
    "Selected ICRS",
  );
  await page.locator("#analysis-tool").selectOption("stack");
  await expect(page.locator("#compute-stack")).toBeVisible();
  await page.locator("#analysis-tool").selectOption("motion");
  await expect(page.locator("#fit-motion")).toBeVisible();
  expect(
    await page.evaluate(() => ({
      selected: window.argusTest.state.selected,
      zoom: window.argusTest.state.zoom,
      panX: window.argusTest.state.panX,
      panY: window.argusTest.state.panY,
    })),
  ).toEqual(before);
  await page.locator("#open-evidence").click();
  await page
    .locator("#note")
    .fill("Image workspace regression annotation; not a scientific claim.");
  await page.locator("#save-mark").click();
  await page.waitForFunction(() => window.argusTest.state.marks.length === 1);
  await page.locator("#save-report").click();
  await expect(page.locator("#toast")).toContainText("Immutable evidence");
});
test("one partial-result notice preserves usable data and exposes retry", async ({
  page,
  request,
}) => {
  const partial = "c296bfa8-cdfb-47e2-82a6-9f7594833cf1";
  test.skip(
    (await request.get("/api/v1/sequences/" + partial)).status() !== 200,
    "Local partial cache not installed",
  );
  await page.goto("/?sequence=" + partial);
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
  await expect(page.locator(".partial-notice")).toHaveCount(1);
  await expect(page.locator(".partial-notice")).not.toContainText("https://");
  let data;
  await page.route("**/api/v1/searches", async (r) => {
    data = r.request().postDataJSON();
    await r.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ sequence: id }),
    });
  });
  await page
    .getByRole("button", { name: "Retry unavailable observations" })
    .click();
  await page.waitForFunction(
    () => window.argusTest.state.manifest.frames.length === 8,
  );
  expect(data.retry_sequence).toBe(partial);
  await expect(page.locator("#partial-summary")).toBeHidden();
});
