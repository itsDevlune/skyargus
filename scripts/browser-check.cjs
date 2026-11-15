const { chromium } = require("@playwright/test");
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2,
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://127.0.0.1:8000/");
  await page.screenshot({
    path: "docs/evidence/explorer-desktop.png",
    fullPage: true,
  });
  console.log(
    "title",
    await page.title(),
    "overflow",
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  );
  await page.getByRole("button", { name: "Open quick start" }).click();
  console.log("help visible", await page.locator("#help-dialog").isVisible());
  await page
    .getByRole("button", { name: "Close", exact: true })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Switch light and dark theme" })
    .click();
  await page.screenshot({
    path: "docs/evidence/explorer-light.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: "docs/evidence/explorer-mobile.png",
    fullPage: true,
  });
  console.log(
    "mobile overflow",
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
  );
  console.log("errors", errors);
  await browser.close();
})();
