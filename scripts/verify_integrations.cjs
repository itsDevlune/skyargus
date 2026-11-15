const { chromium } = require("@playwright/test");
const fs = require("fs");
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2,
  });
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  let requests = 0;
  page.on("request", (r) => {
    if (r.url().includes("/api/v1/searches")) requests++;
  });
  await page.goto("http://127.0.0.1:8000/");
  await page.locator("#detector").selectOption("3");
  await page.locator("button[type=submit]").click();
  await page.waitForFunction(
    () => window.argusTest?.state.manifest?.frames.length === 8,
  );
  await page.waitForFunction(() => window.argusTest.state.images.size > 0);
  const before = requests;
  await page.locator("#zoom-in").click();
  const box = await page.locator("#viewer").boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(
    box.x + box.width / 2 + 30,
    box.y + box.height / 2 + 20,
  );
  await page.mouse.up();
  console.log("pan zoom archive requests", requests - before);
  await page.locator("#reset").click();
  await page.locator("#mark").click();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  await page.locator("#save-mark").click();
  await page.waitForFunction(() => window.argusTest.state.marks.length === 1);
  await page.locator("#next").click();
  await page.mouse.click(box.x + box.width / 2 + 2, box.y + box.height / 2);
  await page.locator("#save-mark").click();
  await page.waitForFunction(() => window.argusTest.state.marks.length === 2);
  await page.locator("#fit-motion").click();
  await page.waitForFunction(
    () =>
      document.getElementById("motion-result").textContent.includes("East "),
    {},
    { timeout: 20000 },
  );
  console.log("motion", await page.locator("#motion-result").innerText());
  await page.locator("#save-report").click();
  await page.waitForFunction(() =>
    document.getElementById("toast").textContent.includes("Immutable evidence"),
  );
  const report = await page.evaluate(async () => {
    const r = await (await fetch("/api/v1/reports")).json();
    return r.reports[0];
  });
  for (const type of ["png", "gif"]) {
    const response = await page.request.get(
      "http://127.0.0.1:8000/api/v1/reports/" + report.id + "/exports/" + type,
    );
    console.log(
      "export",
      type,
      response.status(),
      (await response.body()).length,
    );
    fs.writeFileSync(
      "docs/evidence/report-export." + type,
      await response.body(),
    );
  }
  await page.goto("http://127.0.0.1:8000/reports/" + report.id);
  console.log("reopen", await page.locator("h1").innerText());
  const manifests = JSON.parse(
    fs.readFileSync("docs/evidence/real-manifests.json", "utf8"),
  );
  const native = manifests
    .filter((x) => x.selection.source === "neossat")
    .at(-1);
  await page.goto("http://127.0.0.1:8000/?sequence=" + native.id);
  await page.waitForFunction(
    () => window.argusTest?.state.manifest?.selection.source === "neossat",
  );
  await page.waitForFunction(() => window.argusTest.state.images.size > 0);
  await page.screenshot({
    path: "docs/evidence/neossat-native.png",
    fullPage: true,
  });
  console.log(
    "native mode",
    await page.locator("#release-label").innerText(),
    await page.locator("#sky-label").innerText(),
  );
  console.log("errors", errors);
  await browser.close();
})();
