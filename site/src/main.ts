const data = window.PAGEBOUND_DATA;
const $ = (id) => document.getElementById(id);
let packet = data.packets[0]?.id;
let variant = 'digital';
let pageIndex = 0;
let zoom = 1;
let selectedId = null;
let session = null;
let currentPage;
const pages = () => data.renders.pages.filter(p => p.packet_id === packet && p.rendering === variant);
const regions = () => data.extraction.regions.filter(r => r.render_digest === currentPage?.sha256);
const el = (tag, text, className) => {const node = document.createElement(tag); if(text!==undefined)node.textContent=text; if(className)node.className=className; return node;};
const options = (select, values) => {select.replaceChildren(); values.forEach(([value,text]) => {const o=el('option',text);o.value=value;select.append(o);});};
function selectRegion(id) {
  selectedId=id;
  const r=regions().find(r=>r.id===id);
  $('overlay').replaceChildren();
  document.querySelectorAll('.region-list button').forEach(b=>{b.classList.toggle('selected',b.dataset.id===id);b.setAttribute('aria-pressed',String(b.dataset.id===id));});
  const detail=$('selected-detail');detail.replaceChildren();
  if(!r)return;
  if(r.render_digest!==currentPage.sha256){detail.textContent='Overlay refused: rendering identity mismatch.';return;}
  const polygon=document.createElementNS('http://www.w3.org/2000/svg','polygon');polygon.setAttribute('points',r.polygon.map(p=>p.join(',')).join(' '));$('overlay').append(polygon);
  detail.append(el('span','Native extraction','status'),el('p',r.text),el('p',r.id,'identifier'),el('p','Geometry locates extracted text. Semantic support has not been evaluated.','muted'));
}
function render() {
  const list=pages();pageIndex=Math.min(pageIndex,list.length-1);currentPage=list[pageIndex];
  options($('page'),list.map((p,i)=>[String(i),'PDF page '+(p.physical_page_index+1)]));$('page').value=String(pageIndex);
  $('digital').setAttribute('aria-pressed',String(variant==='digital'));$('scan').setAttribute('aria-pressed',String(variant==='scan'));
  if(!currentPage)return;
  $('document').src=currentPage.display_path;$('document').alt=`${packet}, synthetic PDF page ${currentPage.physical_page_index+1}, ${variant} rendering`;
  $('overlay').setAttribute('viewBox',`0 0 ${currentPage.width} ${currentPage.height}`);
  $('page-label').textContent=`${packet} / PDF page ${currentPage.physical_page_index+1}`;
  $('mode-label').textContent=variant==='scan'?'Image-only scan / designed perturbation':'Digital source / generated fixture';
  $('source-id').textContent='Rendering SHA-256: '+currentPage.sha256;
  $('regions').replaceChildren();const rows=regions();$('region-count').textContent=String(rows.length);
  if(!rows.length)$('regions').append(el('p',variant==='scan'?'This scan has no native text layer. Learned OCR has not run.':'No extracted native text regions.','muted'));
  for(const r of rows){const b=el('button',r.text);b.type='button';b.dataset.id=r.id;b.onclick=()=>selectRegion(r.id);$('regions').append(b);}
  $('structure-rows').replaceChildren();
  for(const r of rows){const tr=el('tr');tr.append(el('td',r.id),el('td',r.text),el('td','Native PDF text, exact rendering'));$('structure-rows').append(tr);}
  selectRegion(rows.some(r=>r.id===selectedId)?selectedId:null);
}
options($('packet'),data.packets.map(p=>[p.id,p.id+' / '+p.title]));
$('packet').onchange=e=>{packet=e.target.value;pageIndex=0;selectedId=null;render();};
$('page').onchange=e=>{pageIndex=Number(e.target.value);selectedId=null;render();};
for(const v of ['digital','scan'])$(v).onclick=()=>{variant=v;render();};
function setZoom(value){zoom=Math.min(2,Math.max(.5,value));$('canvas').style.width=100*zoom+'%';$('canvas').style.maxWidth=650*zoom+'px';$('zoom-label').textContent=Math.round(100*zoom)+'%';}
$('zoom-in').onclick=()=>setZoom(zoom+.25);$('zoom-out').onclick=()=>setZoom(zoom-.25);$('zoom-reset').onclick=()=>setZoom(1);
$('theme').onclick=()=>{const dark=document.body.classList.toggle('dark');$('theme').textContent=dark?'Light theme':'Dark theme';$('theme').setAttribute('aria-pressed',String(dark));};
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>{document.querySelectorAll('.view').forEach(v=>v.hidden=v.id!==button.dataset.view);document.querySelectorAll('[data-view]').forEach(b=>{if(b===button)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});history.replaceState(null,'','#'+button.dataset.view);});
document.querySelectorAll('.statement').forEach(p=>p.textContent=data.summary.statement);
const stats=[['Packets',data.packets.length],['Source pages',new Set(data.renders.pages.map(p=>p.page_id)).size],['Rendered images',data.renders.pages.length],['Native regions',data.extraction.regions.length]];
for(const [label,value] of stats){const a=el('article');a.append(el('strong',String(value)),el('span',label+' / synthetic inventory'));$('inventory').append(a);}
$('manifest').textContent=JSON.stringify({render_manifest:data.renders.render_manifest_digest,extraction:data.extraction.digest,model_study:'not_run',live_api:data.api_url||'not_deployed'},null,2);
for(const item of data.summary.checklist){const d=el('div',undefined,'check');d.append(el('span',String(item.number)),el('span',item.status),el('div',item.requirement));$('checklist').append(d);}
$('crop-max').textContent=data.demo.crop_edge_limit+' pixels';
if(data.api_url){$('run-ocr').disabled=false;$('run-ocr').textContent='Run fresh OCR';}
$('ocr-form').onsubmit=async e=>{e.preventDefault();if(!data.api_url)return;$('run-ocr').disabled=true;$('ocr-status').textContent='Submitting bounded crop';
  try{
    if(!session){const response=await fetch(data.api_url+'/session',{method:'POST'});if(!response.ok)throw Error('Persistent admission unavailable');session=(await response.json()).capability;}
    const bounds=$('crop').value.split(',').map(v=>Number(v.trim()));if(bounds.length!==4||bounds.some(v=>!Number.isFinite(v)))throw Error('Enter four finite bounds');
    const payload={page_id:currentPage.page_id,rendering_id:currentPage.id,render_digest:currentPage.sha256,bounds,idempotency_key:crypto.randomUUID()};
    const response=await fetch(data.api_url+'/ocr',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+session},body:JSON.stringify(payload)});
    const result=await response.json();if(!response.ok)throw Error(result.detail||'OCR unavailable');
    $('ocr-status').textContent=result.execution_mode==='fresh_ocr'?'Fresh learned OCR completed.':result.execution_mode;
    $('receipt').textContent=JSON.stringify(result,null,2);
    if(result.operation_id){const link=el('a','Open persistent receipt');link.href=data.api_url+'/receipts/'+result.operation_id;link.target='_blank';link.rel='noopener noreferrer';$('ocr-status').append(document.createTextNode(' '),link);}
  }catch(err){$('ocr-status').textContent=err.message;}finally{$('run-ocr').disabled=false;}
};
render();
