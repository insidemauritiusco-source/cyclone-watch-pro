const assert=require('node:assert/strict'),{xy,select,frames}=require('./tracker.js');
assert.deepEqual(xy({lat:-4,lon:43}),[0,0]);assert.deepEqual(xy({lat:-29,lon:83}),[1800,1140]);
const n=Date.parse('2026-11-24T12:00:00Z'),t='2026-11-24T12:00:00Z';
const d={source_status:'ok',checked_at:t,storm:{name:'B03',lat:-10,lon:77}};
const b={system_number:3,bulletin_number:1,issued_at:t,anchor:{lat:-10,lon:77},points:[{hours:12,valid_at:'2026-11-25T00:00:00Z',lat:-11,lon:76}]};
const f={schema:1,issuer:'Meteo-France RSMC La Reunion',source:'https://wwmiws.wmo.int/index.php/metareas/bulletinset/8S/html',status:'ok',checked_at:t,bulletins:[b]};
assert.equal(select(d,f,n),b);assert.equal(select(d,f,n+3600000),null);assert.equal(select({...d,storm:{...d.storm,name:'B04'}},f,n),null);assert.equal(select(d,{...f,source:'https://example.com'},n),null);
const hash='a'.repeat(64),m={status:'ok',source:'https://view.eumetsat.int/geoserver/wms',crs:'EPSG:4326',bounds:[43,83,-29,-4],frames:[{captured_at:'2026-11-24T10:00:00Z',sha256:hash,raw:'tracker-media/'+hash+'-raw.jpg'}]};
assert.equal(frames(m,n).length,1);assert.equal(frames({...m,bounds:[0,1,2,3]},n).length,0);assert.equal(frames({...m,frames:[{...m.frames[0],raw:'https://example.com'}]},n).length,0);
console.log('PASS tracker coordinate projection, matched official forecast, stale source rejection and satellite manifest validation');
const {bearing,extent}=require('./tracker.js');
assert.equal(bearing('South Southwest'),202.5);assert.equal(bearing('SSW'),202.5);assert.equal(bearing('stationary'),null);assert.equal(bearing('unknown'),null);
for(const ratio of [.5,1,2,3]){const a=extent(1,ratio,[0,0]);assert.ok(a.box[2]>=1800-1e-6&&a.box[3]>=1140-1e-6);assert.ok(Math.abs(a.box[2]/a.box[3]-ratio)<1e-6);const b=extent(3,ratio,[100,100]);assert.ok(b.box.every(Number.isFinite))}
console.log('PASS tracker viewport fit and reported direction parsing');

const {distance,smartZoom}=require('./tracker.js');
assert.equal(distance({lat:-20.2,lon:57.5},{lat:-20.2,lon:57.5}),0);
assert.equal(distance({lat:-20,lon:57},{lat:-21,lon:57}),111);
assert.equal(distance({lat:NaN,lon:57},{lat:-21,lon:57}),null);
assert.equal(smartZoom({lat:-1,lon:57},1),1);
for(const ratio of [.4,1,2,5])assert.ok(smartZoom({lat:-10,lon:77},ratio)>=2&&smartZoom({lat:-10,lon:77},ratio)<=4);
console.log('PASS V27 distance and smart zoom guards');

const {warningVerified}=require('./tracker.js');
const partial={checked_at:t,source_status:'incomplete',warning_status:'retrieved',storm_status:'empty_page',warning:'No warning reported',storm:null};
assert.equal(warningVerified(partial,n),true);
assert.equal(warningVerified({...partial,warning:'Class II'},n),true);
assert.equal(warningVerified({...partial,warning_status:'unverified'},n),false);
assert.equal(warningVerified({...partial,warning:'Unknown'},n),false);
assert.equal(warningVerified(partial,n+3600000),false);
assert.equal(select(partial,f,n),null);
console.log('PASS independent MMS warning, stale warning rejection and gated storm forecast');
