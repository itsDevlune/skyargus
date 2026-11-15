const {test,expect}=require('@playwright/test');
test('102-channel controls use actual metadata, missing coverage and pixel spectra',async({page})=>{
 // Controlled metadata tests UI state; it is not live archive evidence.
 await page.route('**/api/v1/cubes',r=>r.fulfill({json:{job:'cube-test',status_url:'/api/v1/jobs/cube-test'}}));
 const channels=Array.from({length:102},(_,index)=>({index,detector:Math.floor(index/17)+1,channel:index%17+1,wavelength_um:0.75+index*.04,valid_fraction:index===50?0:.8,available:index!==50}));
 await page.route('**/api/v1/jobs/cube-test',r=>r.fulfill({json:{state:'completed',result:{cube_id:'controlled',channels,date_start:'2025-08-19',date_end:'2026-02-22',warning:'Controlled metadata; not live data',artifact:{url:'/original-cube.fits'}}}}));
 await page.route('**/api/v1/cubes/controlled/planes/*',r=>r.fulfill({status:204}));
 await page.route('**/api/v1/cubes/controlled/spectrum',r=>r.fulfill({json:{coordinates:{ra:269,dec:4},units:'MJy/sr',method:'Controlled sample',warning:'No variance',measurements:channels.map(c=>({index:c.index,wavelength_um:c.wavelength_um,surface_brightness:c.available?c.index/100:null,available:c.available,nhits:c.available?2:0,flags:0}))}}));
 await page.goto('/?sequence=3122bdf8-1727-44ff-ad8c-aac23cffe151');
 await page.waitForFunction(()=>window.argusTest?.state.images.size>0);
 await page.locator('#open-analysis').click();await page.locator('#real-cube-workbench > summary').click();
 await page.locator('#load-real-cube').click();await expect(page.locator('#cube-coverage button')).toHaveCount(102);
 await page.locator('#cube-coverage button').nth(50).click();await expect(page.locator('#cube-channel-label')).toContainText('unavailable');
 await page.locator('#cube-hits').check();await expect(page.locator('#cube-image')).toHaveAttribute('src',/coverage=1/);
 await page.locator('#cube-extract').click();await expect(page.locator('#cube-spectrum table tr')).toHaveCount(103);
 await expect(page.locator('#cube-spectrum')).toContainText('No coverage');await expect(page.locator('#cube-spectrum svg circle')).toHaveCount(101);
});
