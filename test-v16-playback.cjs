const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const nodes=new Map(),timers=new Map();let serial=0;
class Node{constructor(){this.hidden=false;this.disabled=false;this.textContent='';this.value='';this.style={setProperty(){}};this.dataset={};this.options=[];this.children=[]}setAttribute(k,v){this[k]=v}removeAttribute(k){delete this[k]}addEventListener(){}querySelector(){return new Node()}append(n){this.children.push(n)}remove(){}scrollIntoView(){}}
function get(id){if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id)}
get('v15Rate').value='800';get('v16Layer').value='default';get('v16Layer').options=['default','ir','vis','wv'].map(value=>Object.assign(new Node(),{value}));
const frame=(n,p='IR')=>({url:'https://metservice.intnet.mu/mmsimages/'+p+n+'.jpg',captured_at:new Date(Date.now()-n*3600000).toISOString()});
const frames=[frame(2),frame(1)],vis=[frame(3,'VIS'),frame(2,'VIS')],meta={checked_at:new Date().toISOString(),satellite:frames[1],frames,replay:frames,layers:{ir:{frames},vis:{frames:vis}}};
let fail=false;
class FakeImage{set src(v){this.naturalWidth=800;this.naturalHeight=600;if(v==='studio-logo.png')return;if(fail)this.onerror?.();else this.onload?.()}}
const doc={documentElement:{lang:'en'},hidden:false,getElementById:get,querySelectorAll:()=>[],querySelector:()=>new Node(),createElementNS:()=>new Node(),addEventListener(){}};
const ctx={console,document:doc,window:{addEventListener(){}},Image:FakeImage,URL,Date,Intl,AbortSignal,fetch:async()=>({ok:true,json:async()=>meta}),setTimeout:()=>0,clearTimeout(){},setInterval(fn){timers.set(++serial,fn);return serial},clearInterval(id){timers.delete(id)},localStorage:{getItem(){return null}}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('v15.js','utf8'),ctx);
setImmediate(()=>{
 assert.equal(get('v15Count').textContent,'2 / 2');assert.equal(get('v15Image').hidden,false);assert.equal(get('v15Image').src,frames[1].url);
 get('v15Play').onclick();assert.equal(get('v15Count').textContent,'1 / 2');assert.equal(get('v15Play')['aria-pressed'],'true');[...timers.values()].at(-1)();assert.equal(get('v15Count').textContent,'2 / 2');
 get('v15Play').onclick();assert.equal(get('v15Play')['aria-pressed'],'false');
 get('v16Layer').value='vis';get('v16Layer').onchange();assert.equal(get('v15Image').src,vis[1].url);
 get('v16Layer').value='wv';get('v16Layer').onchange();assert.equal(get('v15Count').textContent,'0 / 0');assert.equal(get('v15Image').hidden,true);
 fail=true;get('v16Layer').value='ir';get('v16Layer').onchange();assert.equal(get('v15Image').hidden,true);assert.equal(get('v15MediaBadge').textContent,'Image unavailable');
 console.log('PASS: latest frame, play/pause, chronological advance, layer isolation, unavailable layer, failed-image handling (mocked network).');
});
