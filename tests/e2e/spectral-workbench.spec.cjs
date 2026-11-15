const {test,expect}=require('@playwright/test');
test('wavelength atlas retains actual detector coverage and plots finite uncertainty bars',async({page})=>{
 await page.goto('/?sequence=3122bdf8-1727-44ff-ad8c-aac23cffe151');
 await page.waitForFunction(()=>window.argusTest?.state.images.size>0);
 await page.locator('#open-analysis').click();
 await page.locator('.wavelength-workbench > summary').click();
 await expect(page.locator('.spectral-detector')).toHaveCount(6);
 await expect(page.locator('#spectral-coverage')).toContainText('not a complete 102-channel cube');
 expect(await page.locator('.spectral-samples button').count()).toBe(8);
 await page.locator('.spectral-samples button').first().click();
 await expect(page.locator('#count')).not.toHaveText('0 / 0');
 const plot=await page.evaluate(async()=>{
  const {spectrumPlot}=await import('/static/src/js/spectral-workbench.js');
  const result={measurements:[{wavelength_um:1,flux_mjy:-1,flux_err_mjy:0.2},{wavelength_um:2,flux_mjy:3,flux_err_mjy:0.5},{wavelength_um:NaN,flux_mjy:2}]};
  const svg=spectrumPlot(result);document.querySelector('#analysis-content').append(svg);
  return {dots:svg.querySelectorAll('circle').length,bars:svg.querySelectorAll('line').length,text:svg.textContent,markup:svg.outerHTML};
 });
 expect(plot.dots).toBe(2);expect(plot.bars).toBe(2);
 expect(plot.text).toContain('Flux (mJy)');expect(plot.markup).not.toContain('NaN');
});
