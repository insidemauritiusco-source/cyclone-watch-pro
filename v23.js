(function(factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else{window.cycloneV23=api;api.mount()}})(function(){'use strict';
function reviewReady(values){return Array.isArray(values)&&values.length===3&&values.every(v=>v===true)}
function age(s,now=Date.now()){const t=Date.parse(s);return Number.isFinite(t)&&t<=now+300000?Math.max(0,Math.floor((now-t)/60000)):null}
function assess(v,media,health,report,now=Date.now()){
 const recent=(s,max)=>{const a=age(s,now);return a!==null&&a<=max};
 const times=report?.satellite_frame_times;
 const sequence=Array.isArray(times)&&times.length>0&&times.length===report.satellite_frame_count&&times.every((t,i)=>Number.isFinite(Date.parse(t))&&(!i||Date.parse(t)>Date.parse(times[i-1])));
 return {bulletin:!!(v?.mode==='official'&&v.connected&&!v.stale&&v.data?.source_status==='ok'&&recent(v.data.checked_at,45)),satellite:!!(recent(media?.checked_at,45)&&recent(media?.satellite?.captured_at,360)),health:!!recent(health?.checked_at,45),sequence,review:report?.publication_status==='review_required'&&report?.poster_publication_status==='review_required'};
}
const ids=prefix=>['Dates','Warning','Media'].map(s=>prefix+s);
function ready(prefix){return reviewReady(ids(prefix).map(id=>document.getElementById(id)?.checked===true))}
function reset(prefix){for(const id of ids(prefix)){const el=document.getElementById(id);if(el)el.checked=false}}
function mount(){const $=id=>document.getElementById(id),dialog=$('v20Dialog');let req=0,obsKey='',lastReport=null;
function status(s){$('v23CommandStatus').textContent=s}
$('v23Open').onclick=()=>{$('v21Open').click();if(dialog.open)status('Mode opérationnel · observations datées uniquement.')};
$('v23Satellite').onclick=()=>{$('v22WallLoad').click();$('v22Wall').scrollIntoView({block:'start'});status('Captures MMS datées · pas de flux vidéo continu.')};
async function fullWall(){if(!dialog.open)return;const panel=$('v22Wall').closest('.v22wall');try{if(document.fullscreenElement===panel)await document.exitFullscreen();else if(panel.requestFullscreen)await panel.requestFullscreen();else throw Error('fullscreen')}catch(e){panel.scrollIntoView({block:'start'});status('Plein écran indisponible dans ce navigateur.')}}
$('v23WallFull').onclick=fullWall;$('v23WallRefresh').onclick=()=>$('v22WallLoad').click();
$('v23Map').onclick=()=>{$('v22FocusMap').click();status('Carte géographique · positions observées.')};
function source(type){dialog.close();const el=document.querySelector('[data-layer="'+type+'"]');if(el){el.click();$('layerViewer').scrollIntoView({block:'start'})}}
$('v23Radar').onclick=()=>source('radar');$('v23Forecast').onclick=()=>source('forecast');
$('v23Replay').onclick=()=>{if(!$('v21TrackPlay').disabled){$('v21TrackPlay').click();$('v21Track').scrollIntoView({block:'center'})}else status('Moins de deux observations confirmées : aucune trajectoire à rejouer.')};
$('v23Voice').onclick=()=>{$('v21Presenter').click();$('v21ScriptLoad').click()};
function obs(){const ps=window.cycloneV19?.points(window.cycloneView)||[],k=JSON.stringify(ps);if(k===obsKey)return;obsKey=k;const sel=$('v23Observation');sel.replaceChildren();ps.forEach((p,i)=>{const o=document.createElement('option');o.value=String(i);o.textContent=(i+1)+' · '+p.observed;sel.append(o)});sel.disabled=!ps.length;$('v23Latest').disabled=!ps.length;if(ps.length)sel.value=String(ps.length-1)}
function choose(i){const slider=$('v21TrackSeek');if($('v23Observation').disabled)return;slider.value=String(i);slider.dispatchEvent(new Event('input'));$('v23Observation').value=String(i);$('v21Track').scrollIntoView({block:'nearest'})}
$('v23Observation').onchange=()=>choose(+$('v23Observation').value);$('v23Latest').onclick=()=>choose($('v23Observation').options.length-1);
$('v21TrackSeek').addEventListener('input',()=>{$('v23Observation').value=$('v21TrackSeek').value});
for(const [id,voice] of [['v23FrenchMale','fr-male'],['v23FrenchFemale','fr']])$(id).onclick=()=>{$('videoLanguage').value=voice;$('videoLanguage').dispatchEvent(new Event('change'));if(!$('listenVoice').disabled)$('listenVoice').click()};
for(const [prefix,approve,download] of [['v23Video','approveBroadcast','approvedDownload'],['v23Poster','v21PosterApprove','v21PosterDownload']]){
 for(const id of ids(prefix))$(id).addEventListener('change',()=>{if(!ready(prefix)){$(approve).checked=false;$(download).disabled=true;$(approve).dispatchEvent(new Event('change'))}});
 $(approve).addEventListener('change',()=>{if($(approve).checked&&!ready(prefix)){$(approve).checked=false;$(download).disabled=true;$(approve).dispatchEvent(new Event('change'))}},true)
}
async function json(path){const r=await fetch(path+'?t='+Date.now(),{cache:'no-store',...(typeof AbortSignal!=='undefined'&&AbortSignal.timeout?{signal:AbortSignal.timeout(12000)}:{})});if(!r.ok)throw Error(path);return r.json()}
async function check(){const n=++req;const result=await Promise.allSettled(['media.json','source-health.json','video/source.json'].map(json));if(n!==req)return;const [m,h,r]=result.map(x=>x.status==='fulfilled'?x.value:null),q=assess(window.cycloneView,m,h,r),box=$('v23Health');box.replaceChildren();for(const [label,ok] of [['Recent official bulletin retrieval',q.bulletin],['Recent satellite metadata',q.satellite],['Recent source health record',q.health],['Dated video sequence chronology',q.sequence],['Manual review manifest',q.review]]){const p=document.createElement('p');p.textContent=label+': '+(ok?'Check passed':'Unavailable / unverified');p.dataset.ok=String(ok);box.append(p)}if(lastReport!==null&&lastReport!==r?.generated_at){reset('v23Video');reset('v23Poster');for(const id of ['approveBroadcast','v21PosterApprove']){$(id).checked=false;$(id).dispatchEvent(new Event('change'))}}lastReport=r?.generated_at||null}
$('v23Check').onclick=check;window.addEventListener('cyclone-render',obs);window.addEventListener('online',check);window.addEventListener('offline',check);setInterval(()=>{if(!document.hidden)check()},300000);obs();check();
}
return {reviewReady,ready,reset,age,assess,mount}
});