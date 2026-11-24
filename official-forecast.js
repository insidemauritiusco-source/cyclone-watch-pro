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
function mount(){
 const $=id=>document.getElementById(id),group=$('officialForecastTrack'),status=$('officialForecastStatus'),list=$('officialForecastPoints'),toggle=$('officialForecastToggle');if(!group||!status||!list||!toggle)return;
 let feed=null,seq=0;const ns='http://www.w3.org/2000/svg';
 const date=x=>new Intl.DateTimeFormat('en-GB',{timeZone:'Indian/Mauritius',dateStyle:'medium',timeStyle:'short'}).format(new Date(x))+' MUT';
 function el(tag,attrs,parent=group){const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);parent.append(e);return e}
 function draw(){group.replaceChildren();list.replaceChildren();const b=select(feed,window.cycloneView);if(!b){status.textContent='No current matched official forecast available. Open the official cyclone map.';return}
 status.textContent='Bulletin '+b.bulletin_number+'/'+b.system_number+' · issued '+date(b.issued_at)+' · forecast only, not an observed path.';
 for(const p of b.points){const label=document.createElement('span');label.textContent='+'+p.hours+'h · '+date(p.valid_at)+' · '+Math.abs(p.lat)+'°S, '+p.lon+'°E'+(Date.parse(p.valid_at)<=Date.now()?' · elapsed':'');list.append(label)}
 if(!toggle.checked)return;
 // Plot only explicitly published coordinates. Never join to a newer MMS position.
 const all=[b.anchor,...b.points];for(let i=1;i<all.length;i++){if(!onMap(all[i-1])||!onMap(all[i]))continue;const [x1,y1]=mapPoint(all[i-1]),[x2,y2]=mapPoint(all[i]);el('line',{x1,y1,x2,y2,stroke:'#ffda72','stroke-width':3,'stroke-dasharray':'3 7','stroke-linecap':'round',opacity:'.95'})}
 for(const p of b.points){if(!onMap(p))continue;const [x,y]=mapPoint(p);const dot=el('circle',{cx:x,cy:y,r:5,fill:'#ffda72',stroke:'#071a2c','stroke-width':1.5});el('title',{},dot).textContent='Official forecast +'+p.hours+'h · '+date(p.valid_at);el('text',{x:x+(x>680?-9:9),y:y+15,'text-anchor':x>680?'end':'start'}).textContent='+'+p.hours+'h'}
 }
 async function load(){const id=++seq;try{const r=await fetch('official-forecast.json?t='+Date.now(),{cache:'no-store',...(typeof AbortSignal!=='undefined'&&AbortSignal.timeout?{signal:AbortSignal.timeout(12000)}:{})});if(!r.ok)throw Error('forecast');const data=await r.json();if(id!==seq)return;feed=data}catch(e){if(id!==seq)return;feed=null}draw()}
 toggle.onchange=draw;$('officialForecastRefresh').onclick=load;window.addEventListener('cyclone-render',draw);window.addEventListener('online',load);window.addEventListener('offline',()=>{++seq;feed=null;draw()});setInterval(()=>{if(!document.hidden)load()},300000);setInterval(draw,60000);load()
}
return {select,mapPoint,onMap,mount}
});