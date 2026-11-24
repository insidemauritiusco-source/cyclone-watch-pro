(function(factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else api.mount()})(function(){'use strict';
function quality(meta,voice,format){
 const variant=format==='original'?'original':format;
 const entry=meta?.quality_checks?.[voice]?.[variant];
 const times=meta?.satellite_frame_times;
 const chronology=Array.isArray(times)&&times.length>0&&times.length===meta.satellite_frame_count&&times.every((v,i)=>Number.isFinite(Date.parse(v))&&(!i||Date.parse(v)>Date.parse(times[i-1])));
 const dims={original:[2160,3840],'4k':[2160,3840],hd:[1080,1920],landscape:[1920,1080]}[variant];
 const technical=!!(entry&&dims&&entry.width===dims[0]&&entry.height===dims[1]&&entry.audio===true&&entry.caption_check===true&&Number.isFinite(entry.av_delta)&&entry.av_delta>=0&&entry.av_delta<.2);
 return {technical,chronology,frameCount:chronology?times.length:0,neural:/neural/i.test(meta?.voice?.[voice]||''),review:meta?.publication_status==='review_required'};
}
function pointText(p){return p?[p.observed,p.lat+'°, '+p.lon+'°',Number.isFinite(p.pressure)?p.pressure+' hPa':'Pressure not reported',Number.isFinite(p.wind)?p.wind+' km/h wind':'Wind not reported',Number.isFinite(p.speed)?p.speed+' km/h movement':'Movement not reported',p.direction||'Direction not reported'].join(' · '):'No confirmed observation selected.'}
function mount(){
const $=id=>document.getElementById(id),dialog=$('v20Dialog'),sat=$('v15Satellite'),map=$('v15Track'),timeline=$('v20Timeline'),slots=[[$('v20SatSlot'),sat],[$('v20MapSlot'),map],[$('v20TimelineSlot'),timeline]];
let homes=[],previousFocus=null,playingBefore=false,key='',selected='',metadata=null,lastReportKey='',shown=false;
function fit(){window.dispatchEvent(new Event('resize'))}
function restore(){if(!shown)return;shown=false;for(const [node,marker] of homes){marker.replaceWith(node)}homes=[];if(!playingBefore&&$('v15Play').getAttribute('aria-pressed')==='true')$('v15Play').click();fit();previousFocus?.focus()}
$('v20Open').onclick=()=>{if(shown)return;previousFocus=document.activeElement;playingBefore=$('v15Play').getAttribute('aria-pressed')==='true';homes=slots.map(([slot,node])=>{const marker=document.createComment('V20 original location');node.before(marker);slot.append(node);return [node,marker]});try{dialog.showModal();shown=true;fit();if(!$('geoMap').hidden)$('geoFit').click();render()}catch(e){shown=true;restore()}};
$('v20Close').onclick=()=>dialog.close();dialog.addEventListener('close',restore);
$('v20Fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await dialog.requestFullscreen()}catch(e){$('v20Fullscreen').textContent='Plein écran indisponible'}};
$('v20Pause').onclick=()=>{if(!$('v15Play').disabled)$('v15Play').click();sync()};
function sync(){const p=$('v15Play');$('v20Pause').disabled=p.disabled;$('v20Pause').textContent=p.getAttribute('aria-pressed')==='true'?'Pause des images':'Lire les images'}
new MutationObserver(sync).observe($('v15Play'),{attributes:true,attributeFilter:['disabled','aria-pressed']});
$('v20FrenchVideo').onclick=()=>{$('videoLanguage').value='fr-male';$('broadcastFormat').value='4k';$('videoLanguage').dispatchEvent(new Event('change'));$('videoStudio').scrollIntoView({block:'start'})};
$('v20Refresh').onclick=()=>{$('v19Refresh').click();loadQuality()};
const direction=s=>({north:'Nord',south:'Sud',east:'Est',west:'Ouest',northeast:'Nord-est',northwest:'Nord-ouest',southeast:'Sud-est',southwest:'Sud-ouest',southsouthwest:'Sud-sud-ouest',southsoutheast:'Sud-sud-est',northnorthwest:'Nord-nord-ouest',northnortheast:'Nord-nord-est',eastsoutheast:'Est-sud-est',eastnortheast:'Est-nord-est',westsouthwest:'Ouest-sud-ouest',westnorthwest:'Ouest-nord-ouest'}[String(s||'').toLowerCase().replace(/[^a-z]/g,'')]||s||'—');
function render(){
const v=window.cycloneView,s=v?.mode==='official'?v.storm:null,helper=window.cycloneV19,ok=helper?.fresh(v,helper.age(v?.data?.checked_at));
$('v20Clock').textContent=new Intl.DateTimeFormat('fr-FR',{timeZone:'Indian/Mauritius',dateStyle:'medium',timeStyle:'medium'}).format(new Date())+' MUT';
$('v20TVSystem').textContent=s?.name?.replace('Tropical Disturbance','Perturbation tropicale').replace('Tropical Depression','Dépression tropicale').replace('Tropical Cyclone','Cyclone tropical')||'Système non confirmé';
$('v20TVStatus').textContent=(ok?'Source MMS consultée':'CONDITIONS ACTUELLES NON VÉRIFIÉES')+' · Observation : '+(s?.observed||'indisponible');
$('v20TVPressure').textContent=Number.isFinite(s?.pressure)?s.pressure+' hPa':'—';$('v20TVSpeed').textContent=Number.isFinite(s?.speed)?s.speed+' km/h':'—';$('v20TVDirection').textContent=direction(s?.direction);
$('v20TVWarning').textContent=!ok?'Non vérifié':v.data.warning==='No warning reported'?'Aucun avertissement signalé':/^Class (I|II|III|IV)$/.test(v.data.warning)?v.data.warning.replace('Class','Classe'):'Non vérifié';
$('v20TVStatus').dataset.ok=String(!!ok);
const ps=helper?.points(v)||[];$('v20TimelineNote').textContent=(ok?'Dated official observations. ':'Current source unverified; historical records only. ')+(ps.length===1?'One position; no trajectory yet.':ps.length+' recorded positions; no forecast.');
const nextKey=JSON.stringify(ps);if(nextKey!==key){key=nextKey;const list=$('v20Points');list.replaceChildren();if(!ps.some(p=>p.observed===selected))selected=ps.at(-1)?.observed||'';function choose(p){selected=p.observed;$('v20PointDetail').textContent=pointText(p);for(const button of list.children)button.setAttribute('aria-pressed',String(button.dataset.observed===selected))}
for(const [i,p] of ps.entries()){const button=document.createElement('button');button.type='button';button.dataset.observed=p.observed;button.textContent=(i+1)+' · '+p.observed;button.onclick=()=>choose(p);list.append(button)}const chosen=ps.find(p=>p.observed===selected);if(chosen)choose(chosen);else $('v20PointDetail').textContent=pointText(null)}
sync()}
function showQuality(){const v=$('weatherVideo'),voice=$('videoLanguage').value,fmt=$('broadcastFormat').value,q=quality(metadata,voice,fmt),box=$('v20Quality');box.replaceChildren();const items=[q.technical?'Manifest: dimensions, audio and caption encoding checked':'Technical manifest check unavailable or incomplete',q.chronology?q.frameCount+' dated satellite frames in chronological order':'No verified chronological satellite sequence in manifest',q.neural?'Neural narration reported; listen before approval':'Narration quality requires listening review',q.review?'Manual publication review required':'Publication status not verified'];
if(!v.hidden&&v.readyState>=1)items.push('Device playback metadata: '+v.videoWidth+' × '+v.videoHeight+' · '+(Number.isFinite(v.duration)?v.duration.toFixed(1)+' s':'duration unavailable'));
for(const text of items){const p=document.createElement('p');p.textContent=text;box.append(p)}}
let request=0;async function loadQuality(){const id=++request;try{const r=await fetch('video/source.json?t='+Date.now(),{cache:'no-store',...(typeof AbortSignal!=='undefined'&&AbortSignal.timeout?{signal:AbortSignal.timeout(12000)}:{})});if(!r.ok)throw Error('manifest');const x=await r.json();if(id!==request)return;metadata=x}catch(e){if(id!==request)return;metadata=null}showQuality()}
for(const id of ['videoLanguage','broadcastFormat'])$(id).addEventListener('change',showQuality);$('videoReload').addEventListener('click',loadQuality);$('weatherVideo').addEventListener('loadedmetadata',showQuality);$('weatherVideo').addEventListener('error',showQuality);window.addEventListener('cyclone-render',render);window.addEventListener('online',loadQuality);setInterval(()=>{if(shown)render()},1000);setInterval(()=>{if(!document.hidden)loadQuality()},300000);render();loadQuality();
}
return {quality,pointText,mount}
});