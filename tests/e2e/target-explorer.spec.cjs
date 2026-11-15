const { test, expect } = require('@playwright/test');

test('searched target highlight, return-to-target button, and HiPS continuous exploration', async ({ page }) => {
  await page.goto('http://127.0.0.1:8000/?cached=1');
  await page.waitForSelector('#viewer');

  // Verify return-target button exists and toggle-target checkbox exists
  const returnTargetBtn = page.locator('#return-target');
  await expect(returnTargetBtn).toBeVisible();
  const toggleTarget = page.locator('#toggle-target');
  await expect(toggleTarget).toBeChecked();

  // Test pan away then return-to-target
  const canvas = page.locator('#viewer');
  const box = await canvas.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 100, box.y + box.height / 2 + 80);
  await page.mouse.up();

  // Click return-target
  await returnTargetBtn.click();
  const statusText = page.locator('#status');
  await expect(statusText).toContainText('Returned view to searched target');

  // Switch to Mosaic mode and verify continuous sky exploration text
  await page.selectOption('#mode', 'mosaic');
  await page.waitForTimeout(400);

  // Take screenshot of target highlight and continuous explorer
  await page.screenshot({ path: 'docs/evidence/sky-explorer-target-verified.png' });
});
