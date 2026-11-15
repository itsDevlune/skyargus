const { chromium } = require("@playwright/test");
const fs = require("fs");
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
  await page.goto("http://127.0.0.1:8000/");
  const sequence = JSON.parse(
    fs.readFileSync("docs/evidence/real-manifests.json", "utf8"),
  ).find((s) => s.selection.source === "spherex");
  const frame = sequence.frames[0];
  await page.addScriptTag({
    path: "node_modules/openseadragon/build/openseadragon/openseadragon.min.js",
  });
  const results = await page.evaluate(async (url) => {
    const canvasTimes = [],
      osdTimes = [];
    for (let n = 0; n < 5; n++) {
      let t = performance.now();
      const image = new Image();
      image.src = url;
      await image.decode();
      const c = document.createElement("canvas");
      c.width = 800;
      c.height = 500;
      c.getContext("2d").drawImage(image, 0, 0, 500, 500);
      canvasTimes.push(performance.now() - t);
      const div = document.createElement("div");
      div.style.cssText =
        "position:fixed;left:0;top:0;width:800px;height:500px";
      document.body.append(div);
      t = performance.now();
      await new Promise((resolve, reject) => {
        const viewer = OpenSeadragon({
          element: div,
          showNavigationControl: false,
          tileSources: { type: "image", url, buildPyramid: false },
        });
        viewer.addHandler("open", () => {
          osdTimes.push(performance.now() - t);
          viewer.destroy();
          div.remove();
          resolve();
        });
        viewer.addHandler("open-failed", reject);
      });
    }
    return {
      canvas_ms: canvasTimes,
      openseadragon_ms: osdTimes,
      native_image: "58x58 real SPHEREx preview",
      scope:
        "Five local browser image-open measurements; not WCS accuracy, full playback, archive latency or visitor capacity.",
    };
  }, frame.preview.url);
  fs.writeFileSync(
    "docs/evidence/viewer-benchmark.json",
    JSON.stringify(results, null, 2),
  );
  console.log(results);
  await browser.close();
})();
