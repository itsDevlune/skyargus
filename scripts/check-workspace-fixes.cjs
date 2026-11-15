const { chromium, expect } = require("@playwright/test");
const fs = require("fs");
(async () => {
  fs.mkdirSync("docs/evidence/workspace-fixes", { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: 1,
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(
    "http://127.0.0.1:8000/?sequence=3122bdf8-1727-44ff-ad8c-aac23cffe151",
  );
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
  await page.screenshot({
    path: "docs/evidence/workspace-fixes/desktop.png",
    fullPage: true,
  });
  await page.locator("#mode").selectOption("side");
  await page.screenshot({
    path: "docs/evidence/workspace-fixes/comparison.png",
    fullPage: true,
  });
  await page.goto(
    "http://127.0.0.1:8000/?sequence=c296bfa8-cdfb-47e2-82a6-9f7594833cf1",
  );
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
  await expect(page.locator(".partial-notice")).toContainText(
    "could not be loaded",
  );
  await expect(page.locator(".partial-notice details")).not.toHaveAttribute(
    "open",
  );
  await expect(page.locator(".partial-notice")).not.toContainText("https://");
  await page.screenshot({
    path: "docs/evidence/workspace-fixes/partial.png",
    fullPage: true,
  });
  let retried;
  await page.route("**/api/v1/searches", async (route) => {
    retried = route.request().postDataJSON();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        sequence: "3122bdf8-1727-44ff-ad8c-aac23cffe151",
        cached: true,
      }),
    });
  });
  await page
    .getByRole("button", { name: "Retry unavailable observations" })
    .click();
  await page.waitForFunction(
    () => window.argusTest.state.manifest.frames.length === 8,
  );
  expect(retried.retry_sequence).toBe("c296bfa8-cdfb-47e2-82a6-9f7594833cf1");
  await page.unroute("**/api/v1/searches");
  await page.goto(
    "http://127.0.0.1:8000/?sequence=170f3e57-b16a-48b7-8cb6-818bb55dfd32",
  );
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
  const b = await page.locator("#viewer").boundingBox();
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
  await expect(page.locator("#cursor")).toContainText("Detector pixel");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "docs/evidence/workspace-fixes/mobile.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
  await page.setViewportSize({ width: 1600, height: 1000 });
  await page.goto(
    "http://127.0.0.1:8000/?sequence=64d4984a-57d2-4446-b0fd-ca459e504116",
  );
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
  await expect(page.locator(".partial-notice")).toContainText(
    "4 observations loaded. 4 could not be loaded",
  );
  await expect(page.locator(".partial-notice")).not.toContainText("https://");
  await page.screenshot({
    path: "docs/evidence/workspace-fixes/ngc1760.png",
    fullPage: true,
  });
  console.log(
    "PASS: readable desktop, partial-result summary, retry request, native cursor, mobile, no JS errors.",
  );
  await browser.close();
})();
