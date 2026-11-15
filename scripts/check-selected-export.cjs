const { chromium, expect } = require("@playwright/test");
const fs = require("fs");
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(
    "http://127.0.0.1:8000/?sequence=3122bdf8-1727-44ff-ad8c-aac23cffe151&frame=2",
  );
  await page.waitForFunction(
    () =>
      window.argusTest?.state.index === 2 &&
      window.argusTest.state.images.size > 0,
  );
  await page.locator("#mark").click();
  const box = await page.locator("#viewer").boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await page
    .locator("#note")
    .fill("Export regression check; not a scientific candidate claim.");
  await page.locator("#save-mark").click();
  await page.waitForFunction(() => window.argusTest.state.marks.length === 1);
  await page.locator("#save-report").click();
  await expect(page.locator("#toast")).toContainText("Immutable evidence");
  const selected = await page.evaluate(async () => {
    const list = await (await fetch("/api/v1/reports")).json();
    const r = await (
      await fetch("/api/v1/reports/" + list.reports[0].id)
    ).json();
    return {
      report: r.id,
      index: r.settings.index,
      observation: r.sequence.frames[r.settings.index].id,
    };
  });
  expect(selected.index).toBe(2);
  const response = await page.request.get(
    "http://127.0.0.1:8000/api/v1/reports/" + selected.report + "/exports/png",
  );
  expect(response.status()).toBe(200);
  fs.mkdirSync("docs/evidence/workspace-fixes", { recursive: true });
  fs.writeFileSync(
    "docs/evidence/workspace-fixes/selected-frame.png",
    await response.body(),
  );
  fs.writeFileSync(
    "docs/evidence/workspace-fixes/selected-frame.json",
    JSON.stringify(selected, null, 2),
  );
  console.log("Selected-frame PNG exported:", selected);
  await browser.close();
})();
