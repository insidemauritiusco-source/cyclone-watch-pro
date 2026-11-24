(function(factory){const a=factory();if(typeof module==='object'&&module.exports)module.exports=a;else {window.cycloneV19=a;a.mount()}})(function(){'use strict';
const valid=p=>p&&Number.isFinite(p.lat)&&Number.isFinite(p.lon)&&Math.abs(p.lat)<=90&&Math.abs(p.lon)<=180;
const identity=s=>(String(s||'').match(/\(([A-Za-z0-9-]+)\)\s*$/)?.[1]||String(s||'')).toUpperCase();
function stamp(s){const m=String(s||'').match(/^(\d{1,2}) ([A-Za-z]+) (\d{4}) (\d{1,2})(?::(\d{2}))? (AM|PM)$/i);if(!m)return NaN;const month=['january','february','march','april','may','june','july','august','september','october','november','december'].indexOf(m[2].toLowerCase());if(month<0||+m[1]<1||+m[1]>31||+m[4]<1||+m[4]>12||+(m[5]||0)>59)return NaN;return Date.UTC(+m[3],month,+m[1],+m[4]%12+(m[6].toUpperCase()==='PM'?12:0),+(m[5]||0))}
function points(v){if(v?.mode!=='official'||!v.storm?.name)return [];const id=identity(v.storm.name),p=[...(Array.isArray(v.data?.history)?v.data.history:[]),v.storm];return [...new Map(p.filter(x=>valid(x)&&identity(x.name)===id&&Number.isFinite(stamp(x.observed))).map(x=>[stamp(x.observed),x])).values()].sort((a,b)=>stamp(a.observed)-stamp(b.observed))}
function age(value,now=Date.now()){const t=Date.parse(value);return Number.isFinite(t)&&t<=now+300000?Math.max(0,Math.floor((now-t)/60000)):null}
function fmt(n){return n===null?'Unavailable':n<60?n+' min':Math.floor(n/60)+' h '+n%60+' min'}
function fresh(v,n){return v?.mode==='official'&&v.connected&&!v.stale&&v.data?.source_status==='ok'&&n!==null&&n<=45}
function mount(){const $=id=>document.getElementById(id);let media=null,busy=false,rowsKey='';
function render(){const v=window.cycloneView,b=age(v?.data?.checked_at),m=age(media?.checked_at),s=age(media?.satellite?.captured_at);$('v19BulletinAge').textContent=fmt(b);$('v19MediaAge').textContent=fmt(m);$('v19SatelliteAge').textContent=fmt(s);const ok=fresh(v,b)&&m!==null&&m<=45&&s!==null&&s<=360&&navigator.onLine!==false;
$('v19Status').textContent=ok?'Recent source checks and published satellite metadata. Observation and capture times may differ; image playback is checked separately.':'One or more sources are old, missing, or unverified. Consult official MMS bulletins; this is not an all-clear.';
$('v19Status').dataset.ok=String(!!ok);const ps=points(v);$('v19TrackNote').textContent=ps.length===1?'One recorded position; no observed trajectory yet.':ps.length?ps.length+' dated observations; no extrapolation.':'No confirmed position available.';const key=JSON.stringify(ps);if(key===rowsKey)return;rowsKey=key;const body=$('v19Rows');body.replaceChildren();for(const p of ps.slice(-100).reverse()){const row=document.createElement('tr');for(const val of [p.observed,p.lat+'°, '+p.lon+'°',Number.isFinite(p.pressure)?p.pressure+' hPa':'—',Number.isFinite(p.wind)?p.wind+' km/h':'—',Number.isFinite(p.speed)?p.speed+' km/h':'—']){const td=document.createElement('td');td.textContent=val;row.append(td)}body.append(row)}}
async function check(){if(busy)return;busy=true;try{const r=await fetch('media.json?t='+Date.now(),{cache:'no-store',...(typeof AbortSignal!=='undefined'&&AbortSignal.timeout?{signal:AbortSignal.timeout(12000)}:{})});if(!r.ok)throw Error('metadata');media=await r.json()}catch(e){media=null}finally{busy=false;render()}}
$('v19Regional').onclick=()=>{if($('geoMap').hidden)$('geoToggle').click();$('geoFit').click();$('v15Track').scrollIntoView({block:'start'})};
$('v19Charts').onclick=()=>{$('v17History').click()};
$('v19Refresh').onclick=()=>{$('refresh').click();check()};
$('v19Radar').onclick=()=>{const f=$('v19RadarFrame');f.hidden=false;f.src='https://metservice.intnet.mu/radar-anim.php';$('v19RadarClose').hidden=false};
$('v19RadarClose').onclick=()=>{const f=$('v19RadarFrame');f.hidden=true;f.src='about:blank';$('v19RadarClose').hidden=true};
window.addEventListener('cyclone-render',render);window.addEventListener('offline',render);window.addEventListener('online',check);setInterval(render,60000);setInterval(()=>{if(!document.hidden)check()},300000);render();check();
}
return {points,age,fresh,stamp,mount}
});