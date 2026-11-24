const assert=require('node:assert/strict'),v=require('./v18.js');
assert.equal(v.clampZoom(0),1);assert.equal(v.clampZoom(6),4);assert.equal(v.clampZoom(NaN),1);
assert.equal(v.distance({lat:0,lon:0},{lat:0,lon:0}),0);assert.equal(v.distance({lat:91,lon:0},{lat:0,lon:0}),null);
assert.ok(v.distance({lat:0,lon:0},{lat:0,lon:1})>=111);
assert.equal(v.measure(null,'km/h'),'—');assert.equal(v.measure(0,'km/h'),'0 km/h');
assert.ok(v.retrieved({mode:'official',connected:true,stale:false,data:{source_status:'ok'}}));
assert.ok(!v.retrieved({mode:'demo',connected:true,stale:false,data:{source_status:'ok'}}));
assert.ok(!v.retrieved({mode:'official',connected:true,stale:true,data:{source_status:'ok'}}));
console.log('PASS V18: zoom bounds, island distance, missing measurements and official-source status guards');
