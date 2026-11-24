/* V18 presentation controls only. Official observations remain in the existing updater. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else api.mount()})(this,function(){'use strict';
const islands=[{name:'Mauritius',lat:-20.2,lon:57.5,url:'https://metservice.intnet.mu/tropical-cyclone/current-cyclone.php'},{name:'Rodrigues',lat:-19.71,lon:63.42,url:'https://metservice.intnet.mu/cyclone-bulletin-english-rodrigues.php'},{name:'Réunion',lat:-21.13,lon:55.53,url:'https://meteofrance.re/fr/cyclone'}];
function clampZoom(n){return Math.min(4,Math.max(1,Number.isFinite(n)?n:1))}
function valid(p){return !!p&&Number.isFinite(p.lat)&&Number.isFinite(p.lon)&&Math.abs(p.lat)<=90&&Math.abs(p.lon)<=180}
function distance(a,b){if(!valid(a)||!valid(b))return null;const r=Math.PI/180,x=Math.sin((a.lat-b.lat)*r/2)**2+Math.cos(a.lat*r)*Math.cos(b.lat*r)*Math.sin((a.lon-b.lon)*r/2)**2;return Math.round(12742*Math.asin(Math.sqrt(Math.min(1,Math.max(0,x)))))}
function official(v){return v?.mode==='official'}
function retrieved(v){return official(v)&&v.connected&&!v.stale&&v.data?.source_status==='ok'}
function measure(n,unit){return Number.isFinite(n)?n+' '+unit:'—'}
function mount(){
const $=id=>document.getElementById(id),stage=$('v15Stage'),im=$('v15Image'),panel=$('v15Track');
let zoom=1,fitWidth=0,fitHeight=0,drag=null,tv=false,tick=0,paused=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches||false,lastView=null,islandKey='';
function fit(){if(im.hidden||!im.naturalWidth)return;const w=stage.clientWidth,h=Math.max(160,Math.floor(window.innerHeight*.62));const ratio=Math.min(w/im.naturalWidth,h/im.naturalHeight);fitWidth=Math.floor(im.naturalWidth*ratio);fitHeight=Math.floor(im.naturalHeight*ratio);apply(false)}
function apply(center=true){const x=(stage.scrollLeft+stage.clientWidth/2)/Math.max(1,stage.scrollWidth),y=(stage.scrollTop+stage.clientHeight/2)/Math.max(1,stage.scrollHeight);stage.classList.toggle('v18zoomed',zoom>1);if(fitWidth){im.style.width=Math.round(fitWidth*zoom)+'px';im.style.height=Math.round(fitHeight*zoom)+'px';im.style.maxWidth='none';im.style.maxHeight='none'}$('v18ZoomLabel').textContent=Math.round(zoom*100)+'%';$('v18ZoomOut').disabled=zoom<=1;$('v18ZoomIn').disabled=zoom>=4;if(center){stage.scrollLeft=x*stage.scrollWidth-stage.clientWidth/2;stage.scrollTop=y*stage.scrollHeight-stage.clientHeight/2}}
function change(n){zoom=clampZoom(n);apply()}
$('v18ZoomOut').onclick=()=>change(zoom-.5);$('v18ZoomIn').onclick=()=>change(zoom+.5);$('v18Reset').onclick=()=>{zoom=1;fit();stage.scrollTo(0,0)};
im.addEventListener('load',fit);if(im.complete)fit();window.addEventListener('resize',fit);
stage.addEventListener('pointerdown',e=>{if(zoom<=1||e.pointerType==='touch'||e.button!==0)return;drag={x:e.clientX,y:e.clientY,left:stage.scrollLeft,top:stage.scrollTop};stage.setPointerCapture(e.pointerId)});
stage.addEventListener('pointermove',e=>{if(drag){stage.scrollLeft=drag.left+drag.x-e.clientX;stage.scrollTop=drag.top+drag.y-e.clientY}});
for(const e of ['pointerup','pointercancel','lostpointercapture'])stage.addEventListener(e,()=>{drag=null});
function sync(){const play=$('v15Play'),button=$('v18Loop');button.disabled=play.disabled;const on=play.getAttribute('aria-pressed')==='true';button.setAttribute('aria-pressed',String(on));button.textContent=on?'Pause cloud animation':'Cloud animation';$('v18TrackPlay').disabled=$('trackPlay').disabled}
new MutationObserver(sync).observe($('v15Play'),{attributes:true,attributeFilter:['aria-pressed','disabled']});new MutationObserver(sync).observe($('trackPlay'),{attributes:true,attributeFilter:['disabled']});
$('v18Loop').onclick=()=>{$('v151SatDetails').open=true;$('v15Play').click();sync()};
async function full(el){try{if(document.fullscreenElement)await document.exitFullscreen();else if(el.requestFullscreen)await el.requestFullscreen();else throw Error('unsupported')}catch(e){el.scrollIntoView({block:'start'});$('v18ImageNote').textContent='Full screen unavailable in this browser. Use browser full-screen controls if available.'}}
$('v18SatFull').onclick=()=>full($('v15Satellite'));$('v18MapFull').onclick=()=>full(panel);document.addEventListener('fullscreenchange',fit);
$('v18TrackPlay').onclick=()=>{$('trackPlay').click()};
$('v18Forecast').onclick=()=>{const p=$('v18ForecastPanel');p.hidden=false;$('v18ForecastClose').hidden=false;$('v18ForecastFrame').src='https://metservice.intnet.mu/cyclone-track.php';p.scrollIntoView({block:'nearest'})};
$('v18ForecastClose').onclick=()=>{$('v18ForecastFrame').src='about:blank';$('v18ForecastPanel').hidden=true;$('v18ForecastClose').hidden=true};
$('v18TV').onclick=()=>{tv=!tv;document.body.classList.toggle('v18tv',tv);$('v18TV').setAttribute('aria-pressed',String(tv));$('v18TV').textContent=tv?'Exit TV map mode':'TV map mode';if(tv)window.scrollTo(0,0);fit()};
$('v18VideoFull').onclick=()=>{const video=$('weatherVideo');if(video&&!video.hidden){$('satelliteFull').click()}else $('videoStudio').scrollIntoView({block:'start'})};
function safe(v){return retrieved(v)?'MMS source retrieved · check observation time':'CURRENT CONDITIONS UNVERIFIED · consult official sources'}
function ticker(){const v=lastView;const notes=[safe(v),official(v)?'Reported observation: '+(v?.storm?.observed||'unavailable'):'Simulation is not official data','Independent monitoring · follow official MMS warnings'];$('v18Ticker').textContent=notes[tick%notes.length]}
function pauseLabel(){$('v18TickerToggle').textContent=paused?'Resume graphics':'Pause graphics';$('v18TickerToggle').setAttribute('aria-pressed',String(!paused));$('v18Broadcast').classList.toggle('v18paused',paused)}
$('v18TickerToggle').onclick=()=>{paused=!paused;pauseLabel()};
function render(){const v=window.cycloneView;lastView=v;const s=official(v)?v.storm:null;const ok=retrieved(v);$('v18Headline').textContent=s?.name||'No confirmed system details';$('v18Bulletin').textContent=safe(v)+' · '+(s?.observed||'Observation unavailable');$('v18Pressure').textContent=measure(s?.pressure,'hPa');$('v18Speed').textContent=measure(s?.speed,'km/h');$('v18Direction').textContent=s?.direction||'—';ticker();sync();
const key=JSON.stringify([s?.lat,s?.lon,s?.observed,ok]);if(key===islandKey)return;islandKey=key;const box=$('v18Islands');box.replaceChildren();for(const island of islands){const d=document.createElement('div'),name=document.createElement('b'),val=document.createElement('strong'),note=document.createElement('small'),a=document.createElement('a');name.textContent=island.name;const n=distance(s,island);val.textContent=n===null?'—':n.toLocaleString()+' km';note.textContent=ok?'From reported position':'Current distance unverified';a.href=island.url;a.target='_blank';a.rel='noopener';a.textContent='Official bulletin ↗';d.append(name,val,note,a);box.append(d)}}
window.addEventListener('cyclone-render',render);window.addEventListener('cyclone-language-change',render);setInterval(()=>{if(!paused&&!document.hidden){tick++;ticker()}},6000);pauseLabel();render();
}
return {clampZoom,valid,distance,retrieved,measure,mount}
});