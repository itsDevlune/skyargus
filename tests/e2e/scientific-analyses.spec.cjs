const { test, expect } = require("@playwright/test");

test("scientific analyses in explorer: spectrum, difference, stack and composite", async ({
  page,
  request,
}) => {
  const cachedSequence = await request.get(
    "/api/v1/sequences/360f728f-b81d-409e-b310-70200f4b82cd",
  );
  test.skip(
    cachedSequence.status() !== 200,
    "Local real analysis sequence not installed",
  );
  await page.goto("/?sequence=360f728f-b81d-409e-b310-70200f4b82cd");
  await expect(page.locator("#count")).toContainText("1 / 7");

  // Open Analysis panel
  await page.locator("#open-analysis").click();
  await expect(page.locator("#analysis-content")).toBeVisible();

  // Test Spectrum tool UI
  await page.locator("#analysis-tool").selectOption("spectrum");
  await expect(page.locator("#tool-spectrum-panel")).toBeVisible();
  await expect(page.locator("#extract-spectrum")).toBeVisible();

  // Test Difference tool UI
  await page.locator("#analysis-tool").selectOption("difference");
  await expect(page.locator("#tool-difference-panel")).toBeVisible();
  await expect(page.locator("#compute-difference")).toBeVisible();

  // Test Stacking tool UI
  await page.locator("#analysis-tool").selectOption("stack");
  await expect(page.locator("#tool-stack-panel")).toBeVisible();
  await expect(page.locator("#compute-stack")).toBeVisible();

  // Test Composite tool UI
  await page.locator("#analysis-tool").selectOption("composite");
  await expect(page.locator("#tool-composite-panel")).toBeVisible();
  await expect(page.locator("#compute-composite")).toBeVisible();
});
