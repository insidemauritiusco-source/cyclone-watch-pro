const assert=require('node:assert/strict'),v=require('./v23.js');
assert.equal(v.reviewReady([true,true,true]),true);for(const x of [[],[true,true],[true,false,true],[true,true,1],null])assert.equal(v.reviewReady(x),false);
const now=Date.parse('2026-11-24T09:00:00Z'),t='2026-11-24T08:50:00Z',old='2026-11-24T01:00:00Z';
const view={mode:'official',connected:true,stale:false,data:{source_status:'ok',checked_at:t}},m={checked_at:t,satellite:{captured_at:t}},h={checked_at:t},r={satellite_frame_count:2,satellite_frame_times:['2026-11-24T08:00:00Z',t],publication_status:'review_required',poster_publication_status:'review_required'};
assert.deepEqual(v.assess(view,m,h,r,now),{bulletin:true,satellite:true,health:true,sequence:true,review:true});
assert.equal(v.assess({...view,mode:'demo'},m,h,r,now).bulletin,false);
assert.equal(v.assess(view,{...m,satellite:{captured_at:old}},h,r,now).satellite,false);
assert.equal(v.assess(view,m,h,{...r,satellite_frame_times:[t,t]},now).sequence,false);
assert.equal(v.assess(view,m,h,null,now).review,false);
const fs=require('node:fs');for(const [file,prefix] of [['video-player.js','v23Video'],['v21.js','v23Poster']]){const s=fs.readFileSync(file,'utf8');assert.ok(s.includes("ready('"+prefix+"')"));assert.ok(s.includes("reset('"+prefix+"')"))}
console.log('PASS V23: strict review checklist, simulation exclusion, stale capture and chronology guards, approval integration');
