const { chromium, expect } = require("@playwright/test");
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2,
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://127.0.0.1:8000/");
  await page.locator("#detector").selectOption("3");
  await page.locator("button[type=submit]").click();
  await page.waitForFunction(
    () => window.argusTest?.state.manifest?.frames.length > 0,
    {},
    { timeout: 30000 },
  );
  await page.waitForFunction(() => window.argusTest.state.images.size > 0);
  console.log("real frames", await page.locator("#count").innerText());
  const roundtrip = await page.evaluate(() => {
    const a = window.argusTest,
      p = a.skyToPixel(269.452075, 4.693391),
      s = a.pixelToSky(p.x, p.y);
    return s;
  });
  console.log("high DPI center roundtrip", roundtrip);
  await page.locator("#mark").click();
  const box = await page.locator("#viewer").boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await page
    .locator("#note")
    .fill(
      "Real-data browser verification: compare local response before interpreting brightness.",
    );
  await page.locator("#save-mark").click();
  await page.waitForFunction(() => window.argusTest.state.marks.length === 1);
  await page.locator("#save-report").click();
  await page.waitForFunction(() =>
    document.getElementById("toast").textContent.includes("Immutable evidence"),
  );
  await page.locator("#next").click();
  await page.locator("#mode").selectOption("side");
  await page.waitForTimeout(500);
  await page.screenshot({
    path: "docs/evidence/real-comparison.png",
    fullPage: true,
  });
  await page.locator("#mode").selectOption("single");
  await page.locator("#play").click();
  await page.waitForTimeout(1400);
  await page.locator("#play").click();
  await page.screenshot({
    path: "docs/evidence/real-explorer.png",
    fullPage: true,
  });
  await page.locator("#open-reports").click();
  console.log(
    "report visible",
    await page.locator("#report-list article").count(),
  );
  const share = await page.evaluate(async () => {
    const r = await (await fetch("/api/v1/reports")).json(),
      csrf = document.cookie
        .split("; ")
        .find((x) => x.startsWith("csrftoken="))
        .split("=")[1];
    const s = await (
      await fetch("/api/v1/reports/" + r.reports[0].id + "/shares", {
        method: "POST",
        headers: { "X-CSRFToken": csrf, "Content-Type": "application/json" },
        body: "{}",
      })
    ).json();
    return s;
  });
  await page.goto("http://127.0.0.1:8000" + share.url);
  await page.screenshot({
    path: "docs/evidence/real-report.png",
    fullPage: true,
  });
  console.log(
    "shared report",
    await page.locator("h1").innerText(),
    "images",
    await page.locator(".report-frame").count(),
  );
  console.log("errors", errors);
  await browser.close();
})();
