const { chromium } = require("@playwright/test");
const fs = require("fs");
(async () => {
  const dir = "docs/evidence/explorer-redesign/after";
  fs.mkdirSync(dir, { recursive: true });
  const browser = await chromium.launch();
  const results = [];
  for (const [name, width, height] of [
    ["1366", 1366, 768],
    ["1920", 1920, 1080],
    ["mobile", 390, 844],
  ]) {
    const page = await browser.newPage({ viewport: { width, height } });
    const errors = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(
      "http://127.0.0.1:8000/?sequence=3122bdf8-1727-44ff-ad8c-aac23cffe151",
    );
    await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
    await page.screenshot({ path: `${dir}/${name}.png`, fullPage: true });
    results.push({
      name,
      viewer: await page.locator("#viewer").boundingBox(),
      play: await page.locator("#play").boundingBox(),
      timeline: await page.locator(".timeline").boundingBox(),
      inspectorHidden: await page.locator("#workspace-panel").isHidden(),
      overflow: await page.evaluate(
        () => document.documentElement.scrollWidth > innerWidth,
      ),
      errors,
    });
    await page.close();
  }
  fs.writeFileSync(`${dir}/layout.json`, JSON.stringify(results, null, 2));
  console.log(results);
  await browser.close();
})();
