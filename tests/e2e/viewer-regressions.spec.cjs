const { test, expect } = require("@playwright/test");
const sequence = "3122bdf8-1727-44ff-ad8c-aac23cffe151";
test("cached view restores comparison and display settings without distortion", async ({
  page,
  request,
  context,
}) => {
  const available = await request.get("/api/v1/sequences/" + sequence);
  test.skip(
    available.status() !== 200,
    "Real cached sequence is not installed; offline shell tests remain portable.",
  );
  await page.goto(
    "/?sequence=" +
      sequence +
      "&frame=2&b=1&mode=swipe&zoom=6&contrast=1.8&panX=12&panY=8",
  );
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
  await expect(page.locator("#ab")).toHaveValue("1");
  await expect(page.locator("#stretch")).toHaveValue("1.8");
  expect(
    await page.evaluate(() => [
      window.argusTest.state.panX,
      window.argusTest.state.panY,
    ]),
  ).toEqual([12, 8]);
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.locator("#state-link").click();
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  const copiedParams = new URL(copied).searchParams;
  expect(copiedParams.get("sequence")).toBe(sequence);
  expect(copiedParams.get("panX")).toBe("12");
  expect(copiedParams.get("panY")).toBe("8");
  expect(copiedParams.get("contrast")).toBe("1.8");
  await page.goto(copied);
  await page.waitForFunction(
    () =>
      window.argusTest?.state.manifest?.id ===
        "3122bdf8-1727-44ff-ad8c-aac23cffe151" &&
      window.argusTest.state.zoom === 6 &&
      window.argusTest.state.panX === 12,
  );
  await expect(page.locator("#stretch")).toHaveValue("1.8");
  await expect(page.locator("#ab")).toHaveValue("1");
  await page.evaluate(() => {
    const ctx = document.getElementById("viewer").getContext("2d"),
      original = ctx.drawImage;
    window.regressionDraws = [];
    ctx.drawImage = function (...args) {
      window.regressionDraws.push({
        iw: args[0].naturalWidth,
        ih: args[0].naturalHeight,
        w: args[3],
        h: args[4],
      });
      return original.apply(this, args);
    };
  });
  await page.locator("#mode").selectOption("side");
  await page.waitForTimeout(100);
  const draws = await page.evaluate(() => window.regressionDraws.slice(-2));
  expect(draws.length).toBe(2);
  for (const d of draws) expect(d.w / d.h).toBeCloseTo(d.iw / d.ih, 6);
});
test("desktop defaults to image workspace with collapsed evidence", async ({
  page,
}) => {
  await page.goto("/");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await expect(page.locator("#workspace-panel")).toBeHidden();
  expect(
    await page
      .locator("#ra")
      .evaluate((e) => parseFloat(getComputedStyle(e).fontSize)),
  ).toBeGreaterThanOrEqual(13);
  await page.locator("#open-evidence").click();
  await expect(page.locator("#workspace-panel")).toBeVisible();
  await expect(page.locator("#evidence-panel")).toBeVisible();
});
