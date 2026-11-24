const a=require('node:assert/strict'),v=require('./v22.js'),now=Date.parse('2026-11-24T09:00:00Z');
a.equal(v.sourceStatus({status:'page_reachable',checked_at:'2026-11-24T08:50:00Z'},now),'Page reachable · 10 min ago');
a.equal(v.sourceStatus({status:'page_reachable',checked_at:'2026-11-24T07:00:00Z'},now),'Check unavailable or old');
a.equal(v.sourceStatus(null,now),'Check unavailable or old');
const frame=i=>({url:'https://metservice.intnet.mu/mmsimages/IR'+i+'.jpg',captured_at:new Date(now-i*3600000).toISOString()});
const f=[frame(1),frame(4),frame(2),frame(3),{...frame(5),url:'https://example.com/mmsimages/bad.jpg'},frame(30)];
const result=v.captures({frames:f},'default',now);
a.equal(result.length,3);a.equal(result[0].ts,now-4*3600000);a.equal(result.at(-1).ts,now-3600000);a.deepEqual(v.captures({frames:f},'wv',now),[]);
console.log('PASS V22: regional check age, source URL validation, chronological wall selection, unavailable layers');