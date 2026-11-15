const { chromium, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const out = path.join("docs", "evidence", "application-audit");
fs.mkdirSync(out, { recursive: true });
const results = [];
async function check(name, fn) {
  try {
    const detail = await fn();
    results.push({ name, status: "PASS", detail: detail ?? null });
  } catch (e) {
    results.push({
      name,
      status: "FAIL",
      detail: e.message.split("\n").slice(0, 5).join(" "),
    });
  }
  console.log(results.at(-1));
}
(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    deviceScaleFactor: 2,
    permissions: ["clipboard-read", "clipboard-write"],
  });
  const page = await context.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("http://127.0.0.1:8000/");
  const api = async (url, data, method = "POST") =>
    page.evaluate(
      async ({ url, data, method }) => {
        const csrf = document.cookie
          .split("; ")
          .find((x) => x.startsWith("csrftoken="))
          ?.split("=")[1];
        const r = await fetch(url, {
          method,
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrf || "",
          },
          body: data === undefined ? undefined : JSON.stringify(data),
        });
        return {
          status: r.status,
          data: (r.headers.get("content-type") || "").includes("json")
            ? await r.json()
            : await r.text(),
        };
      },
      { url, data, method },
    );
  await check(
    "Initial sky is empty and playback does not autoplay",
    async () => {
      await expect(page.locator("#empty")).toBeVisible();
      expect(await page.evaluate(() => window.argusTest.state.playing)).toBe(
        false,
      );
    },
  );
  await check("FOV preset controls", async () => {
    for (const n of ["3", "12", "6"]) {
      await page.locator(`[data-fov="${n}"]`).click();
      await expect(page.locator("#width")).toHaveValue(n);
      await expect(page.locator("#height")).toHaveValue(n);
    }
  });
  await check(
    "Five target preset name resolutions (live bounded requests)",
    async () => {
      const resolved = [];
      for (const b of await page.locator("#targets button").all()) {
        await b.click();
        await expect(page.locator("#status")).toHaveText(
          "Reference position resolved",
          { timeout: 20000 },
        );
        resolved.push({
          name: await page.locator("#object").inputValue(),
          ra: await page.locator("#ra").inputValue(),
          dec: await page.locator("#dec").inputValue(),
        });
      }
      return resolved;
    },
  );
  await page.locator("#ra").fill("269.452075");
  await page.locator("#dec").fill("4.693391");
  await page.locator("#detector").selectOption("3");
  await page.locator("button[type=submit]").click();
  await check("Real cached SPHEREx sequence loads", async () => {
    await page.waitForFunction(
      () => window.argusTest.state.manifest?.frames.length === 8,
    );
    await page.waitForFunction(() => window.argusTest.state.images.size > 0);
    return page.evaluate(() => ({
      sequence: window.argusTest.state.manifest.id,
      frames: window.argusTest.state.manifest.frames.length,
      data_mode: window.argusTest.state.manifest.data_mode,
    }));
  });
  const seq = await page.evaluate(() => window.argusTest.state.manifest.id);
  await check("Next, previous and timeline stepping", async () => {
    await page.locator("#next").click();
    await expect(page.locator("#count")).toHaveText("2 / 8");
    await page.locator("#previous").click();
    await expect(page.locator("#count")).toHaveText("1 / 8");
    await page.locator("#timeline").fill("3");
    await expect(page.locator("#count")).toHaveText("4 / 8");
  });
  await check("Keyboard shortcuts and typing isolation", async () => {
    await page.locator("h1").click();
    await page.keyboard.press("ArrowRight");
    await expect(page.locator("#count")).toHaveText("5 / 8");
    await page.locator("#note").fill("audit");
    await page.keyboard.press("ArrowLeft");
    await expect(page.locator("#count")).toHaveText("5 / 8");
  });
  await check("Playback advances and pause stops it", async () => {
    await page.locator("#speed").selectOption("600");
    await page.locator("#play").click();
    await page.waitForTimeout(800);
    await expect(page.locator("#count")).toHaveText("6 / 8");
    await page.locator("#play").click();
    await page.waitForTimeout(800);
    await expect(page.locator("#count")).toHaveText("6 / 8");
  });
  await check("Nonlooping playback stops at last frame", async () => {
    await page.locator("#loop").uncheck();
    await page.locator("#timeline").fill("7");
    await page.locator("#play").click();
    await page.waitForTimeout(800);
    expect(await page.evaluate(() => window.argusTest.state.playing)).toBe(
      false,
    );
    await page.locator("#loop").check();
  });
  await check("A/B blink alternates selected frames", async () => {
    await page.locator("#timeline").fill("2");
    await page.locator("#ab").selectOption("7");
    await page.locator("#mode").selectOption("blink");
    await page.locator("#play").click();
    await page.waitForTimeout(750);
    await expect(page.locator("#count")).toHaveText("8 / 8");
    await page.waitForTimeout(650);
    await expect(page.locator("#count")).toHaveText("3 / 8");
    await page.locator("#play").click();
  });
  await check("Side-by-side preserves image aspect ratio", async () => {
    await page.evaluate(() => {
      window.auditDraws = [];
      const c = document.getElementById("viewer").getContext("2d"),
        original = c.drawImage;
      c.drawImage = function (...args) {
        window.auditDraws.push({
          iw: args[0].naturalWidth,
          ih: args[0].naturalHeight,
          w: args[3],
          h: args[4],
        });
        return original.apply(this, args);
      };
    });
    await page.locator("#mode").selectOption("side");
    await page.waitForTimeout(200);
    const draws = await page.evaluate(() => window.auditDraws.slice(-2));
    expect(draws.length).toBe(2);
    for (const d of draws) expect(d.w / d.h).toBeCloseTo(d.iw / d.ih, 4);
    return draws;
  });
  await check("Swipe control changes comparison rendering", async () => {
    await page.locator("#mode").selectOption("swipe");
    const before = await page.locator("#viewer").screenshot();
    await page.locator("#swipe").fill("90");
    const after = await page.locator("#viewer").screenshot();
    expect(Buffer.compare(before, after)).not.toBe(0);
  });
  await page.locator("#mode").selectOption("single");
  await check(
    "Zoom, pan and reset do not fetch new archive searches",
    async () => {
      let calls = 0;
      const listener = (r) => {
        if (r.url().includes("/api/v1/searches")) calls++;
      };
      page.on("request", listener);
      await page.locator("#zoom-in").click();
      expect(
        await page.evaluate(() => window.argusTest.state.zoom),
      ).toBeGreaterThan(1);
      const b = await page.locator("#viewer").boundingBox();
      await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
      await page.mouse.down();
      await page.mouse.move(b.x + b.width / 2 + 20, b.y + b.height / 2 + 15);
      await page.mouse.up();
      expect(await page.evaluate(() => window.argusTest.state.panX)).not.toBe(
        0,
      );
      await page.locator("#reset").click();
      expect(
        await page.evaluate(() => [
          window.argusTest.state.zoom,
          window.argusTest.state.panX,
          window.argusTest.state.panY,
        ]),
      ).toEqual([1, 0, 0]);
      page.off("request", listener);
      expect(calls).toBe(0);
    },
  );
  await check(
    "High-DPI sky/pixel roundtrip at three field positions",
    async () => {
      const data = await page.evaluate(() => {
        const a = window.argusTest;
        return [
          [269.452075, 4.693391],
          [269.46, 4.7],
          [269.44, 4.68],
        ].map(([ra, dec]) => {
          const p = a.skyToPixel(ra, dec);
          return { ra, dec, actual: a.pixelToSky(p.x, p.y) };
        });
      });
      for (const p of data) {
        expect(p.actual.ra).toBeCloseTo(p.ra, 7);
        expect(p.actual.dec).toBeCloseTo(p.dec, 7);
      }
      return data;
    },
  );
  await check("Fullscreen and exit", async () => {
    await page.locator("#fullscreen").click();
    await page.waitForFunction(() => !!document.fullscreenElement);
    await page.evaluate(() => document.exitFullscreen());
  });
  await check(
    "Display contrast resets without changing original FITS identity",
    async () => {
      const before = await page.evaluate(() =>
        window.argusTest.state.manifest.frames.map((f) => f.original.sha256),
      );
      await page.locator("#stretch").fill("1.8");
      await page.locator("#contrast-reset").click();
      await expect(page.locator("#stretch")).toHaveValue("1");
      expect(
        await page.evaluate(() =>
          window.argusTest.state.manifest.frames.map((f) => f.original.sha256),
        ),
      ).toEqual(before);
    },
  );
  await check(
    "Evidence metadata and native/aligned FITS downloads",
    async () => {
      await expect(page.locator("#evidence")).toContainText("MJy / sr");
      const frame = await page.evaluate(
        () =>
          window.argusTest.state.manifest.frames[window.argusTest.state.index],
      );
      for (const kind of ["original", "aligned"]) {
        const r = await page.request.get(
          "http://127.0.0.1:8000" + frame[kind].url,
        );
        expect(r.status()).toBe(200);
        expect((await r.body()).subarray(0, 6).toString()).toBe("SIMPLE");
      }
      return { id: frame.id, date: frame.date };
    },
  );
  await check(
    "Create, edit, delete annotations and retain other saved marks",
    async () => {
      await page.locator("#mark").click();
      const b = await page.locator("#viewer").boundingBox();
      await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
      await page.locator("#classification").selectOption("artifact");
      await page.locator("#note").fill("Application audit marker");
      await page.locator("#save-mark").click();
      await page.waitForFunction(
        () => window.argusTest.state.marks.length === 1,
      );
      await page.getByRole("button", { name: "Edit", exact: true }).click();
      await page.locator("#note").fill("Edited application audit marker");
      await page.locator("#save-mark").click();
      await page.waitForFunction(
        () => window.argusTest.state.marks[0].revision === 2,
      );
      await expect(page.locator("#marks")).toContainText(
        "Edited application audit marker",
      );
      await page.getByRole("button", { name: "Delete", exact: true }).click();
      await page.waitForFunction(
        () => window.argusTest.state.marks.length === 0,
      );
    },
  );
  await check("Gaia DR3 real queued query and overlay toggle", async () => {
    await page.getByText("Reference context", { exact: true }).click();
    await page.locator("#gaia").click();
    await expect(page.locator("#gaia-result")).toContainText(
      "Gaia DR3 sources",
      { timeout: 90000 },
    );
    const n = await page.evaluate(() => window.argusTest.state.gaia.length);
    expect(n).toBeGreaterThan(0);
    await page.locator("#gaia-visible").uncheck();
    await page.locator("#gaia-visible").check();
    return { count: n, epoch: "J2016.0", propagated: false };
  });
  await page.screenshot({
    path: path.join(out, "explorer-gaia.png"),
    fullPage: true,
  });
  let report;
  await check("Save report from visible UI and reopen", async () => {
    await page.locator("#report-title").fill("Application audit report");
    await page.locator("#save-report").click();
    await expect(page.locator("#toast")).toContainText("Immutable evidence");
    const r = await api("/api/v1/reports", undefined, "GET");
    report = r.data.reports[0];
    await page.goto("http://127.0.0.1:8000/reports/" + report.id);
    await expect(page.locator("h1")).toHaveText("Application audit report");
  });
  await check("JSON, PNG and GIF exports decode", async () => {
    const json = await api("/api/v1/reports/" + report.id, undefined, "GET");
    expect(json.data.immutable).toBe(true);
    for (const [type, signature] of [
      ["png", "89504e470d0a1a0a"],
      ["gif", "474946"],
    ]) {
      const r = await page.request.get(
        "http://127.0.0.1:8000/api/v1/reports/" +
          report.id +
          "/exports/" +
          type,
      );
      expect(r.status()).toBe(200);
      expect(
        (await r.body()).subarray(0, signature.length / 2).toString("hex"),
      ).toBe(signature);
    }
    return {
      revision: json.data.revision,
      frames: json.data.sequence.frames.length,
    };
  });
  await check("Printable report generates PDF", async () => {
    await page.pdf({
      path: path.join(out, "report.pdf"),
      format: "A4",
      printBackground: true,
    });
    expect(fs.statSync(path.join(out, "report.pdf")).size).toBeGreaterThan(
      1000,
    );
  });
  await check("Continue as new revision preserves prior snapshot", async () => {
    await page
      .getByRole("link", { name: "Continue as a new revision" })
      .click();
    await page.waitForFunction(() => window.argusTest?.state.manifest);
    await page.locator("#report-title").fill("Application audit revision 2");
    await page.locator("#save-report").click();
    await expect(page.locator("#toast")).toContainText("Immutable evidence");
    const records = (await api("/api/v1/reports", undefined, "GET")).data
      .reports;
    expect(records[0].revision).toBe(2);
    expect(
      (await api("/api/v1/reports/" + report.id, undefined, "GET")).data.title,
    ).toBe("Application audit report");
  });
  await check(
    "Sharing, separate-session privacy, embed and revocation",
    async () => {
      const s = await api("/api/v1/reports/" + report.id + "/shares", {});
      const other = await browser.newContext();
      const p = await other.newPage();
      const privateResult = await p.request.get(
        "http://127.0.0.1:8000/api/v1/reports/" + report.id,
      );
      expect(privateResult.status()).toBe(404);
      await p.goto("http://127.0.0.1:8000" + s.data.url);
      await expect(p.locator("h1")).toHaveText("Application audit report");
      const embedded = await p.request.get(
        "http://127.0.0.1:8000" + s.data.embed,
      );
      expect(embedded.status()).toBe(200);
      expect(await embedded.text()).not.toContain("<script");
      expect(embedded.headers()["content-security-policy"]).toContain(
        "script-src 'none'",
      );
      await api("/api/v1/reports/" + report.id + "/shares", {}, "DELETE");
      expect(
        (await p.request.get("http://127.0.0.1:8000" + s.data.url)).status(),
      ).toBe(404);
      await other.close();
    },
  );
  await check("Stale report revision is rejected", async () => {
    const r = await api("/api/v1/reports", {
      sequence: seq,
      title: "stale branch",
      parent: report.id,
    });
    expect(r.status).toBe(409);
  });
  await check("Review API creates separate review records", async () => {
    const r = await api("/api/v1/reports/" + report.id + "/reviews", {
      text: "Application audit: review is not scientific confirmation.",
    });
    expect(r.status).toBe(200);
    expect(r.data.reviews.at(-1).text).toContain("Application audit");
  });
  await check("Queued job cancellation (no upstream download)", async () => {
    const r = await api("/api/v1/searches", {
      ra: 269.452075,
      dec: 4.693391,
      detector: 3,
      width: 1.5,
      height: 1.5,
      start: "2099-01-01",
      end: "2099-01-02",
    });
    expect(r.status).toBe(202);
    const c = await api(r.data.status_url, { action: "cancel" });
    expect(["cancelled", "cancel_requested"]).toContain(c.data.state);
    return c.data.state;
  });
  await page.goto(
    "http://127.0.0.1:8000/?sequence=" + seq + "&frame=2&b=1&mode=swipe&zoom=2",
  );
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
  await check("URL restores selected frame, mode and zoom", async () => {
    expect(await page.evaluate(() => window.argusTest.state.index)).toBe(2);
    await expect(page.locator("#mode")).toHaveValue("swipe");
    expect(await page.evaluate(() => window.argusTest.state.zoom)).toBe(2);
  });
  await check("Restored B frame selector matches active B frame", async () => {
    expect(await page.locator("#ab").inputValue()).toBe(
      String(await page.evaluate(() => window.argusTest.state.b)),
    );
  });
  await check("View link retains pan and display contrast", async () => {
    await page.locator("#stretch").fill("1.8");
    await page.locator("#state-link").click();
    const text = await page.evaluate(() => navigator.clipboard.readText());
    const u = new URL(text);
    expect(u.searchParams.get("contrast")).toBe("1.8");
    expect(u.searchParams.has("panX")).toBe(true);
  });
  const manifests = JSON.parse(
    fs.readFileSync("docs/evidence/real-manifests.json", "utf8"),
  );
  const native = manifests
    .filter((m) => m.selection.source === "neossat")
    .at(-1);
  await page.goto("http://127.0.0.1:8000/?sequence=" + native.id);
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
  await check(
    "NEOSSat native playback and honest source controls",
    async () => {
      await expect(page.locator("#source")).toHaveValue("neossat");
      await expect(page.locator("#release")).toBeDisabled();
      await expect(page.locator("#sky-label")).toContainText("uncalibrated");
      await expect(page.locator(".orientation")).toBeHidden();
      await expect(page.locator(".analysis-panel")).toBeHidden();
      await page.locator("#next").click();
      await expect(page.locator("#count")).toHaveText("2 / 4");
    },
  );
  await check(
    "NEOSSat rejects celestial marking with explanation",
    async () => {
      await page.locator("#mark").click();
      const b = await page.locator("#viewer").boundingBox();
      await page.mouse.click(b.x + b.width / 2, b.y + b.height / 2);
      await expect(page.locator("#toast")).toContainText(
        "no validated celestial mapping",
      );
    },
  );
  await check(
    "Native cursor does not claim outside boundary when inside image",
    async () => {
      const b = await page.locator("#viewer").boundingBox();
      await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
      await expect(page.locator("#cursor")).not.toHaveText(
        "Outside loaded boundary",
      );
    },
  );
  await check("Mobile layout, reduced motion and no autoplay", async () => {
    await page.emulateMedia({ reducedMotion: "reduce" });
    await page.setViewportSize({ width: 390, height: 844 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(await page.evaluate(() => window.argusTest.state.playing)).toBe(
      false,
    );
    await page.screenshot({
      path: path.join(out, "native-mobile.png"),
      fullPage: true,
    });
  });
  await check("No uncaught browser JavaScript errors", async () => {
    expect(errors).toEqual([]);
  });
  fs.writeFileSync(
    path.join(out, "results.json"),
    JSON.stringify(
      {
        date: "2026-11-15",
        scope:
          "Current Windows/SQLite local app, real cached observations, bounded live five-name resolutions and one Gaia query. No production/Linux or exhaustive security certification.",
        results,
        errors,
      },
      null,
      2,
    ),
  );
  console.log(
    "TOTAL",
    results.length,
    "PASS",
    results.filter((x) => x.status === "PASS").length,
    "FAIL",
    results.filter((x) => x.status === "FAIL").length,
  );
  await browser.close();
})();
