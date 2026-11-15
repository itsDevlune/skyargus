const {test, expect} = require('@playwright/test');
const fs = require('fs');

test('upstream 502 is distinguished from local quota and preserves loaded observations', async ({page, request}) => {
  const sequence = '93924ac9-a107-4bb6-8f92-e0aee7b106a3';
  test.skip((await request.get('/api/v1/sequences/' + sequence)).status() !== 200, 'Real cached sequence unavailable');
  await page.goto('/?sequence=' + sequence);
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
  await page.route('**/api/v1/searches', route => route.fulfill({status:502, json:{error:{
    code:'archive_temporarily_unavailable', retryable:true,
    message:'Archive returned HTTP 502 (upstream service failure, not an Argus rate limit).'
  }}}));
  await page.locator('button.load').click();
  await expect(page.locator('#status')).toContainText('not an Argus rate limit');
  expect(await page.evaluate(() => window.argusTest.state.manifest.id)).toBe(sequence);
  await expect(page.locator('button.load')).toBeEnabled();
  await page.locator('#next').click();
  await page.waitForFunction(() => window.argusTest.state.index === 1);
});

test('real cached recovery displays its incomplete coverage notice and usable dated frames', async ({page, request}) => {
  const recordPath = 'docs/evidence/cache-recovery/controlled-outage.json';
  test.skip(!fs.existsSync(recordPath), 'Opt-in real cache recovery evidence unavailable');
  const record = JSON.parse(fs.readFileSync(recordPath, 'utf8'));
  test.skip((await request.get('/api/v1/sequences/' + record.sequence)).status() !== 200, 'Local real recovery cache unavailable');
  await page.setViewportSize({width:1366,height:768});
  await page.goto('/?sequence=' + record.sequence);
  await page.waitForFunction(() => window.argusTest?.state.images.size > 0);
  await expect(page.locator('#partial-summary')).toContainText('using saved original FITS');
  await expect(page.getByRole('button', {name:'Retry live archive search'})).toBeVisible();
  await expect(page.locator('#partial-summary')).toContainText('coverage may be incomplete');
  await page.locator('#next').click();
  await page.waitForFunction(() => window.argusTest.state.index === 1);
  await page.screenshot({path:'docs/evidence/cache-recovery/browser-recovered.png',fullPage:true});
});
