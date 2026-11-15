import { $, api, download } from './common.js';
import {createCubeViewer} from './cube-viewer.js';
let cube = null, requestVersion=0;
const viewer=createCubeViewer(()=>cube,(x,y)=>{$('cube-x').value=x;$('cube-y').value=y;$('cube-extract').click();});
function plane() {
  if(!cube)return;
  const i=Number($('cube-channel').value), c=cube.channels[i];
  $('cube-channel-label').textContent=`${i+1}/102 · D${c.detector} channel ${c.channel} · ${c.wavelength_um.toFixed(4)} µm · ${(100*c.valid_fraction).toFixed(1)}% tile coverage${c.available?'':' · unavailable'}`;
  $('cube-image').src=`/api/v1/cubes/${cube.cube_id}/planes/${i}?coverage=${$('cube-hits').checked?1:0}`;
  for(const button of $('cube-coverage').children)button.setAttribute('aria-pressed',String(Number(button.dataset.index)===i));
  viewer.refresh();
}
$('cube-channel').oninput=plane;$('cube-hits').onchange=plane;
$('load-real-cube').onclick=async()=>{
 const selection=window.argusTest?.state?.manifest?.selection;
 if(!selection){$('cube-status').textContent='Load a celestial SPHEREx field first.';return;}
 const version=++requestVersion; $('load-real-cube').disabled=true;
 try{
  const queued=await api('/api/v1/cubes',selection);
  let job;
  for(let n=0;n<600;n++){
   job=await api(queued.status_url,undefined,'GET');
   if(version!==requestVersion)return;
   $('cube-status').textContent=job.stage || job.state;
   if(job.state==='completed')break;
   if(['failed','cancelled','partial'].includes(job.state))throw Error(job.error?.message || 'Cube request did not complete.');
   await new Promise(resolve=>setTimeout(resolve,2000));
  }
  if(job.state!=='completed')throw Error('Cube request timed out. Worker may still be processing; retry can reuse completed cache.');
  cube=job.result;$('cube-workspace').hidden=false;$('cube-status').textContent=`DR1 HPX tile ${cube.tile} · ${cube.date_start} — ${cube.date_end}. ${cube.warning}`;
  $('cube-spectrum').replaceChildren();$('cube-coverage').replaceChildren();
  for(const c of cube.channels){const b=document.createElement('button');b.type='button';b.dataset.index=c.index;b.textContent=c.index+1;b.title=`D${c.detector} / ${c.channel}: ${c.wavelength_um} µm; ${(c.valid_fraction*100).toFixed(1)}% finite/hit coverage`;b.className=c.available?'available':'unavailable';b.onclick=()=>{$('cube-channel').value=c.index;plane();};$('cube-coverage').append(b);}
  $('cube-download').href=cube.artifact.url;
  $('load-real-cube').textContent='Reload cached cube';
  viewer.reset();
  plane();
 }catch(e){
   $('cube-status').textContent=`${e.message} Any completed, verified transfer chunks are retained. Click Resume cube download to continue this field's tile; it does not restart from zero. Keep the worker running.`;
   $('load-real-cube').textContent='Resume cube download';
 }finally{$('load-real-cube').disabled=false;}
};
$('cube-image').onclick=e=>{const r=e.target.getBoundingClientRect();$('cube-x').value=Math.min(511,Math.floor((e.clientX-r.left)/r.width*512));$('cube-y').value=511-Math.min(511,Math.floor((e.clientY-r.top)/r.height*512));$('cube-extract').click();};
async function extractSpectrum(coordinates=null){
 if(!cube)return;const box=$('cube-spectrum');$('cube-extract').disabled=true;$('cube-extract-source').disabled=true;
 const dataset = cube;
 try{const result=await api(`/api/v1/cubes/${dataset.cube_id}/spectrum`,coordinates || {x:Number($('cube-x').value),y:Number($('cube-y').value)});
 if (cube !== dataset) return;
 if(result.pixel){$('cube-x').value=result.pixel.x;$('cube-y').value=result.pixel.y;}
 box.replaceChildren();const p=document.createElement('p');p.textContent=`ICRS ${result.coordinates.ra.toFixed(6)}, ${result.coordinates.dec.toFixed(6)} · ${result.units}. ${result.method} ${result.warning}`;box.append(p);
 const exp=document.createElement('button');exp.textContent='Export cube spectrum JSON';exp.onclick=()=>download('argus-cube-spectrum.json',{cube: cube.artifact,archive_url:cube.archive_url,...result});box.append(exp);
 const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 720 300');svg.setAttribute('role','img');svg.setAttribute('aria-label',`Actual cube pixel spectrum: wavelength in micrometers, surface brightness in ${result.units}; no uncertainty available. Values and gaps in table.`);svg.classList.add('spectrum-plot');
 const good=result.measurements.filter(m=>m.available),vals=good.map(m=>m.surface_brightness),lo=Math.min(0,...vals),hi=Math.max(0,...vals);
 const add=(tag,attrs,text)=>{const el=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))el.setAttribute(k,v);if(text)el.textContent=text;svg.append(el);return el;};
 add('path',{d:'M65 20 V250 H690',stroke:'currentColor',fill:'none'});add('text',{x:12,y:15,fill:'currentColor'},`Surface brightness (${result.units})`);add('text',{x:300,y:292,fill:'currentColor'},'Wavelength (µm)');
 for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4;add('text',{x:60,y:254-220*i/4,fill:'currentColor','text-anchor':'end'},v.toPrecision(3));add('text',{x:65+620*i/4,y:274,fill:'currentColor'},(0.7+4.3*i/4).toFixed(2));}
 for(const m of good)add('circle',{cx:65+(m.wavelength_um-0.7)/4.3*620,cy:250-(m.surface_brightness-lo)/(hi-lo||1)*220,r:3,fill:'#65e2dd'});
 box.append(svg);const table=document.createElement('table');const head=document.createElement('tr');for(const value of ['Channel','µm',result.units,'Hits','Raw flags']){const th=document.createElement('th');th.textContent=value;head.append(th);}table.append(head);
 for(const m of result.measurements){const row=document.createElement('tr');for(const value of [m.index+1,m.wavelength_um,m.surface_brightness??'No coverage',m.nhits,m.flags]){const cell=document.createElement('td');cell.textContent=value;row.append(cell);}table.append(row);}box.append(table);
 }catch(e){if (cube === dataset) box.textContent=e.message;}finally{$('cube-extract').disabled=false;$('cube-extract-source').disabled=false;}
}
$('cube-extract').onclick=()=>extractSpectrum();
$('cube-extract-source').onclick=()=>{
 const state=window.argusTest?.state;
 const position=state?.selected || state?.manifest?.selection;
 if(!position){$('cube-spectrum').textContent='Select a source or load a field first.';return;}
 return extractSpectrum({ra:Number(position.ra),dec:Number(position.dec)});
};
