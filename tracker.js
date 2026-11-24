(function(){'use strict';
const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg',B=[43,83,-29,-4],W=1800,H=1140,src='https://wwmiws.wmo.int/index.php/metareas/bulletinset/8S/html';
const xy=p=>[(p.lon-B[0])/(B[1]-B[0])*W,(B[3]-p.lat)/(B[3]-B[2])*H];
const valid=p=>Number.isFinite(p?.lat)&&Number.isFinite(p?.lon)&&p.lat>=-45&&p.lat<0&&p.lon>=30&&p.lon<=90;
const inMap=p=>valid(p)&&p.lon>=43&&p.lon<=83&&p.lat>=-29&&p.lat<=-4;
const id=s=>String(s||'').match(/\bB0*(\d{1,2})\b/i)?.[1];
const fresh=(s,ms,n=Date.now())=>Number.isFinite(Date.parse(s))&&Date.parse(s)<=n+300000&&n-Date.parse(s)<=ms;
const current=(d,n=Date.now())=>d?.source_status==='ok'&&fresh(d.checked_at,2700000,n);
function select(d,f,n=Date.now()){if(!current(d,n)||!valid(d.storm)||!id(d.storm.name)||f?.schema!==1||f.issuer!=='Meteo-France RSMC La Reunion'||f.source!==src||f.status!=='ok'||!fresh(f.checked_at,2700000,n)||!Array.isArray(f.bulletins))return null;return f.bulletins.filter(b=>b.system_number===+id(d.storm.name)&&Number.isInteger(b.bulletin_number)&&fresh(b.issued_at,86400000,n)&&valid(b.anchor)&&Array.isArray(b.points)&&b.points.length&&b.points.every((p,i)=>valid(p)&&Number.isInteger(p.hours)&&p.hours>(i?b.points[i-1].hours:0)&&p.hours<=120&&Date.parse(p.valid_at)===Date.parse(b.issued_at)+p.hours*3600000)&&b.points.some(p=>Date.parse(p.valid_at)>n)).sort((a,b)=>Date.parse(b.issued_at)-Date.parse(a.issued_at)||b.bulletin_number-a.bulletin_number)[0]||null}
function frames(m,n=Date.now()){if(m?.status!=='ok'||m.source!=='https://view.eumetsat.int/geoserver/wms'||m.crs!=='EPSG:4326'||JSON.stringify(m.bounds)!==JSON.stringify(B)||!Array.isArray(m.frames))return [];return m.frames.filter(f=>fresh(f.captured_at,86400000,n)&&Date.parse(f.captured_at)<=n-3600000&&/^[a-f0-9]{64}$/.test(f.sha256||'')&&/^tracker-media\/[a-f0-9]{64}-raw\.jpg$/.test(f.raw||'')&&(!f.enhanced||/^tracker-media\/[a-f0-9]{64}-ir\.jpg$/.test(f.enhanced))).sort((a,b)=>Date.parse(a.captured_at)-Date.parse(b.captured_at)).filter((f,i,a)=>!i||Date.parse(f.captured_at)>Date.parse(a[i-1].captured_at))}
function bearing(value){
 const names=['north','northnortheast','northeast','eastnortheast','east','eastsoutheast','southeast','southsoutheast','south','southsouthwest','southwest','westsouthwest','west','westnorthwest','northwest','northnorthwest'];
 const short=['n','nne','ne','ene','e','ese','se','sse','s','ssw','sw','wsw','w','wnw','nw','nnw'];
 if(typeof value!=='string')return null;const key=value.toLowerCase().replace(/[\s-]+/g,'');const i=names.includes(key)?names.indexOf(key):short.indexOf(key);return i<0?null:i*22.5;
}
function extent(zoom,ratio,center){
 const q=Number.isFinite(ratio)&&ratio>0?ratio:W/H,z=Math.max(1,Math.min(8,zoom));
 // Fit the full region at 1x, preserving the raster's coordinate transform.
 const w=Math.max(W,H*q)/z,h=w/q;
 const clamp=(v,total,span)=>span>=total?total/2:Math.max(span/2,Math.min(total-span/2,v));
 const x=clamp(center[0],W,w),y=clamp(center[1],H,h);
 return {box:[x-w/2,y-h/2,w,h],center:[x,y]};
}
if(typeof module==='object'){module.exports={xy,select,frames,bearing,extent};return}
let data=null,feed=null,meta=null,images=[],i=0,timer=null,seq=0,enhanced=true,zoom=1,center=[900,570],forecastOn=true,gridOn=true,renderSeq=0;
const fmt=(s,z='Indian/Mauritius')=>Number.isFinite(Date.parse(s))?new Intl.DateTimeFormat('en-GB',{dateStyle:'medium',timeStyle:'short',timeZone:z}).format(new Date(s)):'—';
const val=(v,u='')=>typeof v==='number'&&Number.isFinite(v)?v+u:'—';
function el(tag,attrs,parent){const e=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v));parent.append(e);return e}
function label(g,x,y,s,cls='',size=27){const e=el('text',{x,y,'font-size':size,class:cls},g);e.textContent=s;return e}
function base(){const g=$('grid'),p=$('places');for(let l=45;l<=80;l+=5){let [x]=xy({lat:-4,lon:l});el('line',{x1:x,y1:0,x2:x,y2:H,class:'gridline'},g);label(g,x+7,27,l+'°E','',20)}for(let l=-25;l<=-5;l+=5){let [,y]=xy({lat:l,lon:43});el('line',{x1:0,y1:y,x2:W,y2:y,class:'gridline'},g);label(g,8,y-6,-l+'°S','',20)}for(const [n,lat,lon] of [['Madagascar',-19,46.7],['Mauritius',-20.2,57.5],['Réunion',-21.12,55.53],['Rodrigues',-19.71,63.42],['Agalega',-10.4,56.6],['Diego Garcia',-7.32,72.42]]){let [x,y]=xy({lat,lon});el('circle',{cx:x,cy:y,r:4,fill:'white'},p);label(p,x+10,y-10,n)}}
const map=$('map');
function view(){const r=map.getBoundingClientRect(),e=extent(zoom,r.width/r.height,center);center=e.center;map.setAttribute('viewBox',e.box.join(' '))}
function mapPoint(x,y){const matrix=map.getScreenCTM();if(!matrix)return null;const p=new DOMPoint(x,y).matrixTransform(matrix.inverse());return [p.x,p.y]}
function zoomAt(next,x,y){const old=mapPoint(x,y);zoom=Math.max(1,Math.min(8,next));view();const after=mapPoint(x,y);if(old&&after){center=[center[0]+old[0]-after[0],center[1]+old[1]-after[1]];view()}}
const pointers=new Map();
function gesture(){const p=[...pointers.values()];if(p.length<2)return null;return {x:(p[0].x+p[1].x)/2,y:(p[0].y+p[1].y)/2,d:Math.hypot(p[0].x-p[1].x,p[0].y-p[1].y)}}
map.addEventListener('pointerdown',e=>{if(e.pointerType==='mouse'&&e.button!==0)return;if(pointers.size>=2)return;pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});map.setPointerCapture(e.pointerId);map.classList.add('dragging')});
map.addEventListener('pointermove',e=>{if(!pointers.has(e.pointerId))return;const old=pointers.get(e.pointerId),before=gesture();pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});const after=gesture();if(before&&after&&before.d>4&&after.d>4){const a=mapPoint(before.x,before.y),b=mapPoint(after.x,after.y);if(a&&b){center=[center[0]+a[0]-b[0],center[1]+a[1]-b[1]];view()}zoomAt(zoom*after.d/before.d,after.x,after.y)}else{const a=mapPoint(old.x,old.y),b=mapPoint(e.clientX,e.clientY);if(a&&b){center=[center[0]+a[0]-b[0],center[1]+a[1]-b[1]];view()}}});
for(const ev of ['pointerup','pointercancel','lostpointercapture'])map.addEventListener(ev,e=>{pointers.delete(e.pointerId);if(!pointers.size)map.classList.remove('dragging')});
map.addEventListener('wheel',e=>{e.preventDefault();zoomAt(zoom*Math.exp(-Math.max(-300,Math.min(300,e.deltaY))*.002),e.clientX,e.clientY)},{passive:false});
map.addEventListener('keydown',e=>{const d=75/zoom,delta={ArrowLeft:[-d,0],ArrowRight:[d,0],ArrowUp:[0,-d],ArrowDown:[0,d]}[e.key];if(delta){e.preventDefault();center=[center[0]+delta[0],center[1]+delta[1]];view()}else if(['+','=','-'].includes(e.key)){e.preventDefault();zoom=Math.max(1,Math.min(8,zoom*(e.key==='-'?1/1.4:1.4)));view()}});
function panel(open){$('stormPanel').hidden=!open;document.body.classList.toggle('panel-closed',!open);$('panelToggle').setAttribute('aria-expanded',String(open));view()}
$('panelToggle').onclick=()=>panel($('stormPanel').hidden);$('panelClose').onclick=()=>{panel(false);$('panelToggle').focus()};panel(!matchMedia('(max-width:850px)').matches);
if(typeof ResizeObserver!=='undefined')new ResizeObserver(view).observe(map);else window.addEventListener('resize',view);
function centerOn(p){if(!inMap(p))return;center=xy(p);zoom=2.4;view()}
function dot(g,p,color,r=10){let [x,y]=xy(p);el('circle',{cx:x,cy:y,r,fill:color,stroke:'#091525','stroke-width':4},g);return [x,y]}
function line(g,ps,cls){for(let j=1;j<ps.length;j++)if(inMap(ps[j-1])&&inMap(ps[j])){const a=xy(ps[j-1]),b=xy(ps[j]);el('path',{d:'M'+a.join(',')+' L'+b.join(','),stroke:'#081525','stroke-width':9,fill:'none'},g);el('path',{d:'M'+a.join(',')+' L'+b.join(','),class:cls},g)}}
function draw(){const g=$('tracks');g.replaceChildren();$('points').replaceChildren();const s=data?.storm,ok=current(data),b=select(data,feed);
$('sourceStatus').textContent=ok?'Official MMS source checked '+fmt(data.checked_at)+' MUT':'Source unavailable or stale — consult official MMS';
$('storm').textContent=ok&&s?.name?s.name:'No verified current system';$('obs').textContent=ok&&s?.observed?'Observed: '+s.observed+' (bulletin time)':'Observation unavailable';
$('pressure').textContent=ok?val(s?.pressure,' hPa'):'—';$('speed').textContent=ok?val(s?.speed,' km/h'):'—';$('wind').textContent=ok?val(s?.wind,' km/h'):'—';$('direction').textContent=ok?s?.direction||'—':'—';$('coords').textContent=ok&&valid(s)?Math.abs(s.lat)+'°S · '+s.lon+'°E':'—';$('warning').textContent=ok&&typeof data.warning==='string'?data.warning:'Warning status not verified';
$('centerStorm').disabled=!ok||!inMap(s);
if(ok&&inMap(s)){const hist=(Array.isArray(data.history)?data.history:[]).filter(p=>id(p.name)===id(s.name)&&valid(p));line(g,hist,'observedLine');hist.filter(inMap).forEach(p=>dot(g,p,'#42d9ee',6));let [x,y]=xy(s);
const symbol=el('g',{transform:'translate('+x+' '+y+')',id:'trackerStormSymbol'},g);
el('circle',{cx:0,cy:0,r:27,fill:'none',stroke:'#071525','stroke-width':9},symbol);
el('circle',{cx:0,cy:0,r:27,fill:'none',stroke:'#42d9ee','stroke-width':4,class:'storm-ring'},symbol);
const spiral=el('g',{class:'storm-spin'},symbol);
el('path',{d:'M-23 -5 C-23 -31 26 -25 18 -4 Q12 9 0 0 M23 5 C23 31 -26 25 -18 4 Q-12 -9 0 0',fill:'none',stroke:'#071525','stroke-width':9,'stroke-linecap':'round'},spiral);
el('path',{d:'M-23 -5 C-23 -31 26 -25 18 -4 Q12 9 0 0 M23 5 C23 31 -26 25 -18 4 Q-12 -9 0 0',fill:'none',stroke:'#42d9ee','stroke-width':5,'stroke-linecap':'round'},spiral);
el('circle',{r:6,fill:'#42d9ee',stroke:'#071525','stroke-width':2},symbol);
const deg=bearing(s.direction);
if(deg!==null&&Number.isFinite(s.speed)&&s.speed>0){const rad=deg*Math.PI/180,dx=Math.sin(rad)*W/40/Math.cos(s.lat*Math.PI/180),dy=-Math.cos(rad)*H/25,len=Math.hypot(dx,dy),ux=dx/len,uy=dy/len,ex=ux*70,ey=uy*70;
const arrow=el('g',{id:'trackerMovementArrow','data-bearing':deg},symbol);const title=el('title',{},arrow);title.textContent='Reported MMS movement: '+s.direction+'; not a forecast';
const path='M'+(ux*30)+' '+(uy*30)+' L'+ex+' '+ey+' M'+(ex-ux*14-uy*9)+' '+(ey-uy*14+ux*9)+' L'+ex+' '+ey+' L'+(ex-ux*14+uy*9)+' '+(ey-uy*14-ux*9);
el('path',{d:path,fill:'none',stroke:'#071525','stroke-width':10,'stroke-linejoin':'round'},arrow);el('path',{d:path,fill:'none',stroke:'#42d9ee','stroke-width':5,'stroke-linejoin':'round'},arrow)}
label(g,x>W-300?x-35:x+35,y-35,'MMS observation','',25).setAttribute('text-anchor',x>W-300?'end':'start')}
$('forecastStatus').textContent=b?'Issued '+fmt(b.issued_at)+' MUT · published positions only':'No current matched official forecast available';
if(b){if(forecastOn){line(g,[b.anchor,...b.points],'forecastLine');if(inMap(b.anchor))dot(g,b.anchor,'#ffda72',7);b.points.forEach((p,j)=>{if(inMap(p)){let [x,y]=dot(g,p,'#ffda72');const side=x>W-250||j%2===0?-1:1,tx=Math.max(80,Math.min(W-80,x+side*78)),ty=Math.max(34,Math.min(H-34,y+(j%2?44:-42)));el('line',{x1:x,y1:y,x2:tx,y2:ty,stroke:'#ffda72','stroke-width':2},g);const text=label(g,tx,ty,'+'+p.hours+'h','forecastLabel',26);text.setAttribute('text-anchor',side<0?'end':'start');const tip=el('title',{},text);tip.textContent=fmt(p.valid_at)+' MUT · official forecast'}})}b.points.forEach(p=>{let e=document.createElement('button');e.className='point';let span=document.createElement('span');span.textContent='+'+p.hours+'h';e.append(span,document.createTextNode(fmt(p.valid_at)+' MUT · '+Math.abs(p.lat)+'°S '+p.lon+'°E'+(Number.isFinite(p.max_wind_kt)?' · '+p.max_wind_kt+' kt':'')));e.disabled=!inMap(p);e.onclick=()=>centerOn(p);$('points').append(e)})}}
function stop(){clearInterval(timer);timer=null;$('play').textContent='▶ Play'}
function frame(){if(!images.length){$('sat').removeAttribute('href');$('frameTime').textContent='—';$('imageStatus').textContent='Satellite imagery unavailable';return}const f=images[i],url=enhanced&&f.enhanced?f.enhanced:f.raw,k=++renderSeq;const im=new Image();im.onload=()=>{if(k!==renderSeq)return;$('sat').setAttribute('href',url);$('imageStatus').textContent=(enhanced&&f.enhanced?'Enhanced IR':'Original IR')+' · delayed observation';$('frameTime').textContent=fmt(f.captured_at,'UTC')+' UTC / '+fmt(f.captured_at)+' MUT · '+(i+1)+'/'+images.length};im.onerror=()=>{if(k===renderSeq){$('sat').removeAttribute('href');$('imageStatus').textContent='Satellite frame unavailable';$('frameTime').textContent='—'}};im.src=url;$('seek').value=i}
function play(){if(timer){stop();return}if(images.length<2)return;$('play').textContent='❚❚ Pause';timer=setInterval(()=>{if(i===images.length-1&&!$('loop').checked){stop();return}i=(i+1)%images.length;frame()},1200/Number($('rate').value))}
async function get(p){try{const r=await fetch(p+'?t='+Date.now(),{cache:'no-store',signal:AbortSignal.timeout(12000)});return r.ok?await r.json():null}catch{return null}}
async function refresh(){const k=++seq;const [d,f,m]=await Promise.all([get('data.json'),get('official-forecast.json'),get('tracker-media/manifest.json')]);if(k!==seq)return;data=d;feed=f;meta=m;const next=frames(m);if(JSON.stringify(next)!==JSON.stringify(images)){stop();renderSeq++;images=next;i=Math.max(0,images.length-1);$('seek').max=i;$('seek').disabled=images.length<2;$('play').disabled=images.length<2;frame()}if(!images.length)frame();if(m?.coast==='tracker-media/coast.png')$('coast').setAttribute('href',m.coast);else $('coast').removeAttribute('href');$('credit').textContent='EUMETSAT Meteosat · '+(m?.coast?'Natural Earth coastlines · ':'coastlines unavailable · ')+'Delayed observed imagery';draw()}
base();view();$('play').onclick=play;$('seek').oninput=()=>{i=+$('seek').value;frame()};$('rate').onchange=()=>{if(timer){stop();play()}};$('infra').onclick=()=>{enhanced=true;$('infra').setAttribute('aria-pressed','true');$('raw').setAttribute('aria-pressed','false');frame()};$('raw').onclick=()=>{enhanced=false;$('raw').setAttribute('aria-pressed','true');$('infra').setAttribute('aria-pressed','false');frame()};$('forecastToggle').onclick=()=>{forecastOn=!forecastOn;$('forecastToggle').setAttribute('aria-pressed',forecastOn);draw()};$('gridToggle').onclick=()=>{gridOn=!gridOn;$('gridToggle').setAttribute('aria-pressed',gridOn);$('grid').style.display=gridOn?'':'none'};$('zoomIn').onclick=()=>{zoom=Math.min(8,zoom*1.4);view()};$('zoomOut').onclick=()=>{zoom=Math.max(1,zoom/1.4);view()};$('reset').onclick=()=>{zoom=1;center=[900,570];view()};$('centerStorm').onclick=()=>centerOn(data?.storm);$('centerMU').onclick=()=>centerOn({lat:-20.2,lon:57.5});$('refresh').onclick=refresh;$('full').onclick=()=>{if(document.fullscreenElement)document.exitFullscreen().catch(()=>{});else document.documentElement.requestFullscreen?.().catch(()=>{})};function clock(){$('clock').textContent=fmt(new Date().toISOString())+' MUT'}clock();setInterval(clock,1000);setInterval(refresh,300000);window.addEventListener('offline',()=>{$('sourceStatus').textContent='Offline — official status cannot be verified';data=null;draw()});refresh();
})();