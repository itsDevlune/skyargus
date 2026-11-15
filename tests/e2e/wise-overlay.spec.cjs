const {test,expect}=require('@playwright/test');
test('AllWISE reference overlay loads, toggles, and reports upstream failure',async({page})=>{
 await page.route('**/api/v1/catalogs/wise',route=>route.fulfill({json:{job:'wise-ui',status_url:'/api/v1/jobs/wise-ui'}}));
 await page.route('**/api/v1/jobs/wise-ui',route=>route.fulfill({json:{state:'completed',result:{sources:[{ra:'269.452075',dec:'4.693391',designation:'controlled-test'}],warning:'Positions not propagated.',possibly_truncated:false}}}));
 await page.goto('/?sequence=3122bdf8-1727-44ff-ad8c-aac23cffe151');
 await page.waitForFunction(()=>window.argusTest?.state.images.size>0);
 await page.locator('#open-evidence').click();
 await page.getByText('Reference context',{exact:true}).click();
 await page.locator('#wise').click();
 await expect(page.locator('#wise-result')).toContainText('1 AllWISE sources');
 expect(await page.evaluate(()=>window.argusTest.state.wise.length)).toBe(1);
 await page.locator('#wise-visible').uncheck();
 await expect(page.locator('#wise-visible')).not.toBeChecked();
 await page.locator('#wise-visible').check();
 await page.route('**/api/v1/catalogs/wise',route=>route.fulfill({status:502,json:{error:{message:'Controlled upstream unavailable'}}}));
 await page.locator('#wise').click();
 await expect(page.locator('#wise-result')).toContainText('Controlled upstream unavailable');
 expect(await page.evaluate(()=>window.argusTest.state.wise.length)).toBe(1);
});
