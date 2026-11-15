import { $, toast } from './common.js';

// A loaded exposure is not a nominal channel: retain actual wavelength/date
// identity rather than assigning guessed channel numbers to LVF samples.
export function renderCoverage(manifest) {
  const host = $('spectral-coverage');
  host.replaceChildren();
  const intro = document.createElement('p');
  intro.className = 'tiny';
  intro.textContent = 'Explore loaded wavelength samples across six detectors. SPHEREx has 102 nominal channels; this bounded exposure selection is not a complete 102-channel cube. Wavelengths below are field-center lookups. Missing detectors remain unavailable. Broad-band sums are not calibrated photometry.';
  host.append(intro);
  if (manifest.geometry.mode === 'native') {
    intro.textContent = 'Wavelength analysis requires celestial SPHEREx observations.';
    return;
  }
  for (let detector = 1; detector <= 6; detector++) {
    const rows = manifest.frames.map((frame,index)=>({frame,index}))
      .filter(({frame})=>Number(frame.detector ?? manifest.selection.detector)===detector)
      .sort((a,b)=>(a.frame.wavelength?.[0] ?? Infinity)-(b.frame.wavelength?.[0] ?? Infinity));
    const group = document.createElement('section'); group.className='spectral-detector';
    const title=document.createElement('h3'); title.textContent=`Detector ${detector} · ${rows.length} loaded exposures`;
    group.append(title);
    if (!rows.length) {
      const empty=document.createElement('p'); empty.className='tiny'; empty.textContent='No loaded data. Choose this detector in Request settings and Load observations.';group.append(empty);
    }
    const bands=document.createElement('div');bands.className='spectral-samples';
    for (const {frame,index} of rows) {
      const button=document.createElement('button');button.type='button';
      button.textContent=frame.wavelength ? `${frame.wavelength[0].toFixed(3)} µm` : 'Wavelength unavailable';
      button.title=`Frame ${index+1} · ${frame.date || 'Unknown date'} · ${frame.id}`;
      button.setAttribute('aria-label',`${button.textContent}, frame ${index+1}, ${frame.date || 'unknown date'}`);
      button.onclick=()=>{$('timeline').value=index;$('timeline').dispatchEvent(new Event('input'));};
      bands.append(button);
    }
    group.append(bands);
    if(rows.length>1){
      const prepare=document.createElement('button');prepare.type='button';prepare.textContent='Prepare compatible detector stack';
      prepare.onclick=()=>{
        // The first wavelength-sorted exposure is the explicit reference.
        // Server checks and weighting remain authoritative.
        const reference=rows[0].frame.wavelength;
        if(!reference){toast('Reference bandpass unavailable.');return;}
        const selected=rows.filter(({frame})=>{
          const w=frame.wavelength;
          return w && Math.min(reference[0]+reference[1]/2,w[0]+w[1]/2)>Math.max(reference[0]-reference[1]/2,w[0]-w[1]/2);
        }).map(row=>row.index);
        if(selected.length<2){toast('No overlapping repeated samples for this detector; do not stack disjoint wavelengths.');return;}
        $('analysis-tool').value='stack';$('analysis-tool').dispatchEvent(new Event('change'));
        for(const input of $('stack-frame-checkboxes').querySelectorAll('input'))input.checked=selected.includes(Number(input.value));
        toast(`Prepared ${selected.length} nominally overlapping exposures using ${reference[0].toFixed(3)} µm as reference. Review dates and warnings, then Stack selected frames.`);
      };group.append(prepare);
    }
    host.append(group);
  }
}

export function spectrumPlot(result) {
  const points=result.measurements.filter(p=>Number.isFinite(p.wavelength_um)&&Number.isFinite(p.flux_mjy));
  if(!points.length)return document.createTextNode('No finite spectrum measurements to plot.');
  const ns='http://www.w3.org/2000/svg';const svg=document.createElementNS(ns,'svg');
  svg.setAttribute('viewBox','0 0 720 300');svg.setAttribute('role','img');svg.setAttribute('aria-label','Quick-look spectrum: wavelength in micrometers versus flux in millijanskys. Error bars show reported flux uncertainty. Measurements are not joined across dates or gaps; full values in table.');svg.classList.add('spectrum-plot');
  const minX=Math.min(...points.map(p=>p.wavelength_um)),maxX=Math.max(...points.map(p=>p.wavelength_um));
  const errors=points.map(p=>Number.isFinite(p.flux_err_mjy)?Math.abs(p.flux_err_mjy):0);
  const minY=Math.min(0,...points.map((p,i)=>p.flux_mjy-errors[i])),maxY=Math.max(...points.map((p,i)=>p.flux_mjy+errors[i]));
  const x=v=>65+(v-minX)/(maxX-minX||1)*620,y=v=>250-(v-minY)/(maxY-minY||1)*220;
  function element(tag,attrs,text){const e=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);if(text)e.textContent=text;svg.append(e);return e;}
  element('path',{d:'M65 25 V250 H690',fill:'none',stroke:'currentColor'});
  element('text',{x:300,y:292,fill:'currentColor'},'Wavelength (µm)');
  element('text',{x:12,y:16,fill:'currentColor'},'Flux (mJy)');
  for(let i=0;i<=4;i++){
    const xv=minX+(maxX-minX)*i/4,yv=minY+(maxY-minY)*i/4;
    element('text',{x:x(xv),y:272,fill:'currentColor','text-anchor':'middle'},xv.toFixed(3));
    element('text',{x:58,y:y(yv)+4,fill:'currentColor','text-anchor':'end'},yv.toPrecision(3));
  }
  points.forEach((p,i)=>{
    element('line',{x1:x(p.wavelength_um),x2:x(p.wavelength_um),y1:y(p.flux_mjy-errors[i]),y2:y(p.flux_mjy+errors[i]),stroke:'#65e2dd','stroke-width':2});
    const dot=element('circle',{cx:x(p.wavelength_um),cy:y(p.flux_mjy),r:4,fill:'#b9a5ff'});
    const title=document.createElementNS(ns,'title');title.textContent=`${p.observation_id} · ${p.date} · ${p.wavelength_um} µm · ${p.flux_mjy} ± ${p.flux_err_mjy ?? 'unavailable'} mJy`;dot.append(title);
  });return svg;
}
