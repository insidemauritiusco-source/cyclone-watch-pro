(function(factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else api.mount()})(function(){'use strict';
const source='https://wwmiws.wmo.int/index.php/metareas/bulletinset/8S/html';
function fresh(s,max,now){const t=Date.parse(s);return Number.isFinite(t)&&t<=now+300000&&now-t<=max}
function number(s){const m=String(s||'').match(/\bB0*(\d{1,2})\b/i);return m?+m[1]:null}
function inside(p){return Number.isFinite(p?.lat)&&Number.isFinite(p?.lon)&&p.lat<0&&p.lat>=-45&&p.lon>=30&&p.lon<=90}
function select(feed,v,now=Date.now()){
 if(!v||v.mode!=='official'||!v.connected||v.stale||v.data?.source_status!=='ok'||!fresh(v.data.checked_at,2700000,now))return null;
 const n=number(v.storm?.name);if(!n||!inside(v.storm)||!feed||feed.schema!==1||feed.issuer!=='Meteo-France RSMC La Reunion'||feed.source!==source||feed.status!=='ok'||!fresh(feed.checked_at,2700000,now)||!Array.isArray(feed.bulletins))return null;
 const candidates=feed.bulletins.filter(b=>b.system_number===n&&fresh(b.issued_at,86400000,now)&&Number.isInteger(b.bulletin_number)&&inside(b.anchor)&&Array.isArray(b.points)&&b.points.length&&b.points.every((p,i)=>inside(p)&&Number.isInteger(p.hours)&&p.hours>0&&p.hours<=120&&Date.parse(p.valid_at)===Date.parse(b.issued_at)+p.hours*3600000&&(!i||p.hours>b.points[i-1].hours))&&b.points.some(p=>Date.parse(p.valid_at)>now)).sort((a,b)=>Date.parse(b.issued_at)-Date.parse(a.issued_at)||b.bulletin_number-a.bulletin_number);
 return candidates[0]||null
}
function mapPoint(p){return [35+(p.lon-43)/40*730,25+(-4-p.lat)/25*390]}
function onMap(p){return p.lon>=43&&p.lon<=83&&p.lat>=-29&&p.lat<=-4}
const classes=new Set(['VERY INTENSE TROPICAL CYCLONE','INTENSE TROPICAL CYCLONE','TROPICAL CYCLONE','SEVERE TROPICAL STORM','MODERATE TROPICAL STORM','TROPICAL DEPRESSION','TROPICAL DISTURBANCE','POST-TROPICAL DEPRESSION','REMNANT LOW','EXTRATROPICAL DEPRESSION']);
function intensity(p){const wind=Number.isInteger(p?.max_wind_kt)&&p.max_wind_kt>=0&&p.max_wind_kt<=200?p.max_wind_kt+' kt (10-min average)':'Not reported';const classification=classes.has(p?.classification)?p.classification:'Not reported';return {wind,classification}}
function nextStep(index,count){return index+1<count?index+1:null}
function mount(){
 const $=id=>document.getElementById(id),group=$('officialForecastTrack'),status=$('officialForecastStatus'),list=$('officialForecastPoints'),toggle=$('officialForecastToggle');if(!group||!status||!list||!toggle)return;
 let feed=null,seq=0,key='',index=0,timer=null;const ns='http://www.w3.org/2000/svg',play=$('forecastPlay'),replay=$('forecastReplay'),seek=$('forecastSeek'),rate=$('forecastRate'),step=$('forecastStep'),detail=$('forecastDetail');
 const date=x=>new Intl.DateTimeFormat('en-GB',{timeZone:'Indian/Mauritius',dateStyle:'medium',timeStyle:'short'}).format(new Date(x))+' MUT';
 function el(tag,attrs,parent=group){const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);parent.append(e);return e}
 function stop(){if(timer!==null){clearInterval(timer);timer=null}play.textContent='Play forecast';play.setAttribute('aria-pressed','false')}
 function schematic(){if(!$('geoMap').hidden)$('geoToggle').click()}
 function draw(){
 group.replaceChildren();list.replaceChildren();const b=select(feed,window.cycloneView);
 const nextKey=b?JSON.stringify([b.system_number,b.bulletin_number,b.issued_at,b.anchor,b.points]):'';
 if(nextKey!==key){stop();key=nextKey;index=0}
 const available=!!b&&toggle.checked;play.disabled=!available||b.points.length<2;replay.disabled=play.disabled;seek.disabled=play.disabled;rate.disabled=play.disabled;
 seek.max=String(b?b.points.length-1:0);seek.value=String(b?Math.min(index,b.points.length-1):0);
 if(!available)stop();
 if(!b){status.textContent='No current matched official forecast available. Open the official cyclone map.';step.textContent='—';detail.textContent='No verified forecast selected.';return}
 status.textContent='Bulletin '+b.bulletin_number+'/'+b.system_number+' · issued '+date(b.issued_at)+' · forecast only, not an observed path.';
 const now=Date.now(),p=b.points[index],iData=intensity(p);
 step.textContent=(index+1)+' / '+b.points.length+' · +'+p.hours+'h · '+date(p.valid_at);
 detail.textContent='Forecast position: '+Math.abs(p.lat)+'°S, '+p.lon+'°E · '+iData.classification+' · Max sustained wind: '+iData.wind+(Date.parse(p.valid_at)<=now?' · Elapsed forecast (not an observation).':'')+(!onMap(p)?' · Outside this map extent.':'');
 for(const [i,q] of b.points.entries()){const button=document.createElement('button');button.type='button';button.className='forecast-point-button';button.textContent='+'+q.hours+'h · '+date(q.valid_at)+(Date.parse(q.valid_at)<=now?' · elapsed':'');button.setAttribute('aria-pressed',String(i===index));button.disabled=!available;button.onclick=()=>{stop();schematic();index=i;draw()};list.append(button)}
 if(!toggle.checked)return;
 // Plot only issued coordinates. The selected ring jumps between them; never interpolate.
 const all=[b.anchor,...b.points];for(let i=1;i<all.length;i++){if(!onMap(all[i-1])||!onMap(all[i]))continue;const [x1,y1]=mapPoint(all[i-1]),[x2,y2]=mapPoint(all[i]);el('line',{x1,y1,x2,y2,stroke:'#ffda72','stroke-width':3,'stroke-dasharray':'3 7','stroke-linecap':'round',opacity:'.95'})}
 for(const [i,q] of b.points.entries()){if(!onMap(q))continue;const [x,y]=mapPoint(q);if(i===index)el('circle',{id:'forecastSelectedPoint',cx:x,cy:y,r:11,class:'forecast-highlight'});const dot=el('circle',{cx:x,cy:y,r:i===index?6:5,fill:'#ffda72',stroke:'#071a2c','stroke-width':1.5});el('title',{},dot).textContent='Official forecast +'+q.hours+'h · '+date(q.valid_at);el('text',{x:x+(x>680?-9:9),y:y+15,'text-anchor':x>680?'end':'start'}).textContent='+'+q.hours+'h'}
 }
 function startPlayback(restart=false){const b=select(feed,window.cycloneView);if(!b||!toggle.checked||b.points.length<2){stop();draw();return}schematic();stop();if(restart||index===b.points.length-1)index=0;draw();play.textContent='Pause forecast';play.setAttribute('aria-pressed','true');timer=setInterval(()=>{const current=select(feed,window.cycloneView);if(!current||!toggle.checked||JSON.stringify([current.system_number,current.bulletin_number,current.issued_at,current.anchor,current.points])!==key){stop();draw();return}const n=nextStep(index,current.points.length);if(n===null){stop();draw();return}index=n;draw();if(index===current.points.length-1)stop()},Number(rate.value)||1200)}
 async function load(){const id=++seq;try{const r=await fetch('official-forecast.json?t='+Date.now(),{cache:'no-store',...(typeof AbortSignal!=='undefined'&&AbortSignal.timeout?{signal:AbortSignal.timeout(12000)}:{})});if(!r.ok)throw Error('forecast');const data=await r.json();if(id!==seq)return;feed=data}catch(e){if(id!==seq)return;feed=null}draw()}
 play.onclick=()=>{if(timer!==null){stop();return}startPlayback()};replay.onclick=()=>startPlayback(true);rate.onchange=()=>{if(timer!==null)startPlayback()};seek.oninput=()=>{stop();schematic();index=Number(seek.value);draw()};
 $('forecastFull').onclick=()=>{schematic();$('v18MapFull').click()};
 toggle.onchange=()=>{if(toggle.checked)schematic();draw()};$('officialForecastRefresh').onclick=load;window.addEventListener('cyclone-render',draw);window.addEventListener('online',load);window.addEventListener('offline',()=>{++seq;feed=null;draw()});document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else load()});setInterval(()=>{if(!document.hidden)load()},300000);setInterval(draw,60000);load()

}
return {select,mapPoint,onMap,intensity,nextStep,mount}
});