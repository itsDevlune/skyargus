const {chromium, expect} = require('@playwright/test');
const fs = require('fs');
(async()=>{
 const browser=await chromium.launch();
 const context=await browser.newContext({viewport:{width:1366,height:768},permissions:['clipboard-read','clipboard-write']});
 const page=await context.newPage(); const errors=[]; page.on('pageerror',e=>errors.push(e.message));
 const root='http://127.0.0.1:8000'; const dir='docs/evidence/ui-roundtrip'; fs.mkdirSync(dir,{recursive:true});
 await page.goto(root+'/?sequence=3122bdf8-1727-44ff-ad8c-aac23cffe151');
 await page.waitForFunction(()=>window.argusTest?.state.images.size>0);
 await page.locator('#next').click(); await page.locator('#stretch').fill('1.5');
 await page.locator('#mark').click(); const box=await page.locator('#viewer').boundingBox();
 await page.mouse.click(box.x+box.width/2,box.y+box.height/2);
 await page.locator('#note').fill('Frontend round-trip: real cached observation; manual association only.');
 await page.locator('#save-mark').click(); await expect(page.locator('#marks')).toContainText('Frontend round-trip');
 await page.screenshot({path:dir+'/evidence.png',fullPage:true});
 await page.locator('#close-panel').click(); await page.locator('#next').click();
 await page.mouse.click(box.x+box.width/2,box.y+box.height/2);
 await page.locator('#note').fill('Second dated manual association for motion workflow verification.');
 await page.locator('#save-mark').click();
 await expect(page.locator('#marks')).toContainText('Second dated');
 await page.locator('#previous').click();
 await page.locator('#report-title').fill('Frontend acceptance round-trip');
 await page.locator('#save-report').click();
 await expect(page.locator('#toast')).toContainText('Immutable evidence report saved');
 const report=await page.evaluate(async()=>{const list=await(await fetch('/api/v1/reports')).json();return await(await fetch('/api/v1/reports/'+list.reports[0].id)).json()});
 expect(report.settings.index).toBe(1); expect(report.candidates.some(c=>c.note.includes('Frontend round-trip'))).toBe(true);
 fs.writeFileSync(dir+'/report.json',JSON.stringify(report,null,2));
 for(const format of ['png','gif']) {const response=await context.request.get(root+'/api/v1/reports/'+report.id+'/exports/'+format);expect(response.ok()).toBe(true);fs.writeFileSync(dir+'/report.'+format,await response.body());}
 await page.goto(root+'/reports/'+report.id); await expect(page.locator('h1')).toHaveText(report.title);
 await page.screenshot({path:dir+'/report-page.png',fullPage:true}); await page.pdf({path:dir+'/report.pdf'});
 await page.getByText('Continue as a new revision').click();
 await page.waitForFunction(()=>window.argusTest?.state.index===1&&window.argusTest.state.images.size>0);
 await expect(page.locator('#stretch')).toHaveValue('1.5');
 expect(await page.evaluate(()=>window.argusTest.state.selected)).not.toBeNull();
 await page.locator('#open-analysis').click(); await page.locator('#analysis-tool').selectOption('spectrum');
 await page.screenshot({path:dir+'/analysis.png',fullPage:true});
 const analyses=await page.evaluate(async()=>{
  const csrf=document.cookie.split('; ').find(x=>x.startsWith('csrftoken=')).split('=')[1];
  const sequence=window.argusTest.state.manifest.id;
  const requests=[{method:'spectrum',ra:269.452075,dec:4.693391,aperture_radius_pix:3},{method:'difference',frame_a:0,frame_b:1},{method:'stack',frames:[0,1]},{method:'composite',red:0,green:1,blue:2},{method:'motion',position_error_arcsec:3.1}];
  const results=[];
  for(const payload of requests){const response=await fetch('/api/v1/analyses',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:JSON.stringify({sequence,...payload})});results.push({method:payload.method,status:response.status,result:await response.json()});}
  return results;
 });
 fs.writeFileSync(dir+'/analysis-submissions.json',JSON.stringify(analyses,null,2));
 for(const analysis of analyses){if(!analysis.result.job)continue;let job;for(let attempt=0;attempt<30;attempt++){job=await(await context.request.get(root+'/api/v1/jobs/'+analysis.result.job)).json();if(['completed','failed','cancelled'].includes(job.state))break;await page.waitForTimeout(500);}analysis.completedJob=job;}
 fs.writeFileSync(dir+'/analysis-results.json',JSON.stringify(analyses,null,2));
 const share=await page.evaluate(async(id)=>{const csrf=document.cookie.split('; ').find(x=>x.startsWith('csrftoken=')).split('=')[1];return await(await fetch('/api/v1/reports/'+id+'/shares',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':csrf},body:'{}'})).json()},report.id);
 const guest=await browser.newContext();const view=await guest.newPage();await view.goto(root+share.url);
 await expect(view.locator('h1')).toHaveText(report.title);expect(await view.locator('#save-report').count()).toBe(0);
 await page.evaluate(async(id)=>{const csrf=document.cookie.split('; ').find(x=>x.startsWith('csrftoken=')).split('=')[1];await fetch('/api/v1/reports/'+id+'/shares',{method:'DELETE',headers:{'X-CSRFToken':csrf}})},report.id);
 expect((await view.goto(root+share.url)).status()).toBe(404);
 fs.writeFileSync(dir+'/results.json',JSON.stringify({report:report.id,restoredFrame:1,restoredContrast:1.5,selected:true,shareRevoked:true,errors},null,2));
 expect(errors).toEqual([]); await browser.close();console.log('round-trip passed',report.id);
})().catch(e=>{console.error(e);process.exit(1)});
