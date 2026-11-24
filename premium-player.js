(function(factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else api.mount()})(function(){'use strict';
const FILE='satellite-fullscreen-4k.mp4',OVERLAY='satellite-fullscreen-forecast-4k.mp4',SOURCE='https://view.eumetsat.int/geoserver/wms';
const timestamp=s=>typeof s==='string'&&/(Z|[+-]\d\d:\d\d)$/.test(s)&&Number.isFinite(Date.parse(s));
function select(m,variant='observed'){
 const g=m?.geographic_satellite_overlay,frames=g?.frames;
 if(m?.preview_only!==false||m?.publication_status!=='review_required'||m?.premium_satellite_publication_status!=='review_required'||m?.premium_satellite_fullscreen!==FILE||!timestamp(m.generated_at)||g?.status!=='ok'||g.source!==SOURCE||g.crs!=='EPSG:4326'||!Array.isArray(frames)||frames.length<2||frames.length>96)return null;
 if(!frames.every((f,i)=>timestamp(f?.captured_at)&&Date.parse(f.captured_at)<=Date.parse(m.generated_at)&&(!i||Date.parse(f.captured_at)>Date.parse(frames[i-1].captured_at))&&/^[a-f0-9]{64}$/.test(f?.sha256?.wide||'')))return null;
 const b=m.official_forecast,issued=Date.parse(b?.issued_at),validPoint=p=>Number.isFinite(p?.lat)&&p.lat>=-45&&p.lat<0&&Number.isFinite(p?.lon)&&p.lon>=30&&p.lon<=90;
 const overlay=m.premium_satellite_forecast===OVERLAY&&timestamp(b?.issued_at)&&validPoint(b?.anchor)&&Array.isArray(b?.points)&&b.points.length>0&&b.points.every((p,i)=>validPoint(p)&&Number.isInteger(p.hours)&&p.hours>(i?b.points[i-1].hours:0)&&p.hours<=120&&timestamp(p.valid_at)&&Date.parse(p.valid_at)===issued+p.hours*3600000)&&b.points.some(p=>Date.parse(p.valid_at)>Date.parse(m.generated_at));
 if(variant==='forecast'&&!overlay)return null;
 const file=variant==='forecast'?OVERLAY:FILE;
 const dates=frames.map(f=>f.captured_at),key=JSON.stringify([m.generated_at,m.observation_key,m.report_key,file,variant==='forecast'?b:null,g.source,g.layer,g.crs,g.credit,g.coastline,g.bounds,frames]);
 return {file,overlay,variant,generated:m.generated_at,dates,key,credit:typeof g.credit==='string'?g.credit:'EUMETSAT Meteosat',coast:typeof g.coastline==='string'?g.coastline:'Not available',enhanced:frames.some(f=>f.brightness_enhanced?.wide===true)};
}
function reviewReady(checks,loaded,confirmed){return loaded===true&&confirmed===true&&checks.length===3&&checks.every(x=>x===true)}
function mount(){
 const $=id=>document.getElementById(id),v=$('premiumVideo'),status=$('premiumStatus'),review=$('premiumReview'),approve=$('premiumApprove'),approved=$('premiumApproved'),download=$('premiumDownload'),checks=['premiumCheckDates','premiumCheckWarning','premiumCheckMedia'].map($),buttons=['premiumPlay','premiumReplay','premiumFull'].map($);
 let current=null,loaded=false,seq=0,epoch=0,busy=false;const variant=$('premiumVariant'),loop=$('premiumLoop');v.loop=loop.checked;loop.onchange=()=>{v.loop=loop.checked};variant.onchange=()=>{refresh(true)};
 const fmt=(t,z)=>new Intl.DateTimeFormat('en-GB',{timeZone:z,dateStyle:'medium',timeStyle:'short'}).format(new Date(t));
 const url=s=>'video/'+s.file+'?v='+encodeURIComponent(s.generated);
 const checked=()=>checks.map(x=>x.checked);
 function sync(){const ok=!!current&&loaded&&!v.error;for(const el of checks)el.disabled=!ok;approve.disabled=!ok||!checked().every(Boolean);if(approve.disabled)approve.checked=false;approved.disabled=busy||!reviewReady(checked(),ok,approve.checked);for(const el of buttons)el.disabled=!ok;download.hidden=!ok;review.textContent=!approved.disabled?'Approved on this device for manual publication only. Nothing posted.':'Review required · No automatic social publication.'}
 function reset(){epoch++;for(const el of checks)el.checked=false;approve.checked=false;busy=false;sync()}
 function fail(message){current=null;loaded=false;v.pause();v.removeAttribute('src');v.hidden=true;v.load();download.removeAttribute('href');$('premiumDates').textContent='';$('premiumCredit').textContent='';reset();status.textContent=message}
 async function manifest(){const r=await fetch('video/source.json?t='+Date.now(),{cache:'no-store',...(typeof AbortSignal!=='undefined'&&AbortSignal.timeout?{signal:AbortSignal.timeout(12000)}:{})});if(!r.ok)throw Error('manifest');const raw=await r.json();const base=select(raw);variant.options[1].disabled=!base?.overlay;return select(raw,variant.value)}
 async function refresh(force=false){const id=++seq;try{const m=await manifest();if(id!==seq)return;if(!m){fail('Selected dated satellite clip is unavailable. Select observed imagery or refresh.');return}if(current?.key===m.key&&!force)return;current=m;loaded=false;v.pause();reset();v.hidden=false;v.src=url(m);download.href=url(m);download.download='Inside-Mauritius-'+m.variant+'-satellite-review.mp4';$('premiumDates').textContent=m.dates.length+' observed frames · '+fmt(m.dates[0],'UTC')+' UTC to '+fmt(m.dates.at(-1),'UTC')+' UTC · '+fmt(m.dates[0],'Indian/Mauritius')+' MUT to '+fmt(m.dates.at(-1),'Indian/Mauritius')+' MUT · generated '+fmt(m.generated,'Indian/Mauritius')+' MUT';$('premiumCredit').textContent=m.credit+' · Coastlines: '+m.coast+(m.enhanced?' · Colours represent IR display brightness, not temperature or cyclone intensity.':'');status.textContent='Loading dated 4K satellite clip…';v.load()}catch(e){if(id===seq)fail('Satellite video manifest unavailable. Refresh when connected.')}}
 v.addEventListener('loadedmetadata',()=>{if(!current)return;if(v.videoWidth!==3840||v.videoHeight!==2160||!Number.isFinite(v.duration)||v.duration<=0){fail('Satellite video dimensions could not be verified.');return}loaded=true;status.textContent='4K UHD · '+v.duration.toFixed(1)+' s · '+(current.variant==='forecast'?'Dated forecast overlay, not observed movement':'Dated observations, not live');sync()});
 v.addEventListener('error',()=>{if(!current)return;loaded=false;reset();status.textContent='4K video playback unavailable on this device. Try another browser or refresh.'});
 $('premiumPlay').onclick=()=>{if(!loaded)return;if(v.paused)v.play().catch(()=>{status.textContent='Playback unavailable. Try the native video controls.'});else v.pause()};
 $('premiumReplay').onclick=()=>{if(loaded){v.currentTime=0;v.play().catch(()=>{status.textContent='Replay unavailable. Try the native video controls.'})}};
 v.addEventListener('play',()=>{$('premiumPlay').textContent='Pause';document.getElementById('weatherVideo')?.pause()});
 for(const ev of ['pause','ended'])v.addEventListener(ev,()=>{$('premiumPlay').textContent='Play'});
 $('weatherVideo')?.addEventListener('play',()=>v.pause());
 $('premiumFull').onclick=async()=>{if(!loaded)return;try{if(v.requestFullscreen)await v.requestFullscreen();else if(v.webkitEnterFullscreen)v.webkitEnterFullscreen();else throw Error('fullscreen')}catch(e){status.textContent='Full screen unavailable here. Use the native player controls or Open full app.'}};
 $('premiumRefresh').onclick=()=>refresh(true);
 for(const el of [...checks,approve])el.addEventListener('change',()=>{epoch++;sync()});
 approved.onclick=async()=>{if(approved.disabled||!current)return;const before=current,revision=epoch;busy=true;sync();review.textContent='Rechecking exact satellite clip…';try{const latest=await manifest();if(!latest||latest.key!==before.key||current?.key!==before.key||revision!==epoch||!reviewReady(checked(),loaded&&!v.error,approve.checked))throw Error('changed');const link=document.createElement('a');link.href=url(before);link.download=before.variant==='forecast'?'Inside-Mauritius-approved-forecast-satellite-4k.mp4':'Inside-Mauritius-approved-satellite-4k.mp4';link.click();busy=false;sync();review.textContent='Approved download requested. No social media post sent.'}catch(e){reset();review.textContent='Clip changed or review could not be verified. Refresh and review again.'}};
 window.addEventListener('online',()=>refresh());window.addEventListener('offline',()=>{++seq;fail('Offline. Reconnect to verify the dated satellite video.')});
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});setInterval(()=>{if(!document.hidden)refresh()},300000);
 sync();refresh();
}
return {select,reviewReady,mount};
});