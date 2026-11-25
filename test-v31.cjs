'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {assess,inspect,verifyApproval,allowed}=require('./v31-review.cjs');
const n=Date.parse('2026-11-24T12:00:00Z'),iso=x=>new Date(x).toISOString();
const d={source_status:'ok',checked_at:iso(n-60000),errors:[],warning:'No warning reported',storm:{name:'Tropical Disturbance (B03)',observed:'24 November 2026 12 PM',lat:-10,lon:77}};
const m={preview_only:false,publication_status:'review_required',source_status:'ok',generated_at:iso(n-30000),checked_at:d.checked_at,warning:d.warning,observation:d.storm,official_forecast:null,satellite_url:'https://metservice.intnet.mu/mmsimages/test.jpg',satellite_frame_count:2,satellite_frame_times:[iso(n-7200000),iso(n-3600000)],observation_key:'a'.repeat(64),report_key:'b'.repeat(64),videos:{},formats:{},quality_checks:{},previews:{},captions:{}};
const sizes={original:[2160,3840],'4k':[2160,3840],hd:[1080,1920],landscape:[1920,1080],landscape4k:[3840,2160]};
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'v31-test-'));
try{
for(const voice of ['fr','mfe']){
 m.videos[voice]='weather-'+voice+'.mp4';m.formats[voice]={};m.quality_checks[voice]={};m.previews[voice]='voice-'+voice+'.mp3';m.captions[voice]='captions-'+voice+'.vtt';
 for(const [fmt,[width,height]] of Object.entries(sizes)){
 const file='weather-'+voice+(fmt==='original'?'':'-'+fmt)+'.mp4';m.formats[voice][fmt]=file;m.quality_checks[voice][fmt]={width,height,audio:true,caption_check:true,av_delta:.05};fs.writeFileSync(path.join(dir,file),'fixture');
 }
 for(const name of [m.previews[voice],m.captions[voice],'narration-'+voice+'.txt'])fs.writeFileSync(path.join(dir,name),'fixture');
}
fs.writeFileSync(path.join(dir,'source.json'),JSON.stringify(m));
assert.deepEqual(assess(m,d,null,n),[]);
for(const [bad,pattern] of [
 [{...m,preview_only:true},/reviewable/],[{...m,warning:'Class I'},/warning/],[{...m,observation:{...d.storm,lat:-11}},/coordinates/],[{...m,satellite_url:'https://example.com/mmsimages/test.jpg'},/imagery/],[{...m,satellite_frame_times:[...m.satellite_frame_times].reverse()},/imagery/],[{...m,satellite_frame_times:[iso(n-7200000),iso(n+60000)]},/imagery/],[{...m,generated_at:iso(n-7200000)},/timestamp/],[{...m,official_forecast:{system_number:3}},/forecast/],[{...m,quality_checks:{}},/manifest/]])assert.match(assess(bad,d,null,n).join(';'),pattern);
assert.match(assess(m,{...d,checked_at:iso(n-3600000)},null,n).join(';'),/stale/);
assert.match(assess(m,{...d,errors:['failed']},null,n).join(';'),/unavailable/);
let count=0;const fakeProbe=()=>count++;const p=inspect(dir,d,null,n,fakeProbe);assert.equal(count,10);
const a={...p,schema:1,status:'approved',run_id:'123',approved_by:'editor',approved_at:iso(n)};
assert.equal(verifyApproval(a,p,'123'),true);assert.equal(verifyApproval(null,p,'123'),false);assert.equal(verifyApproval(a,p,'124'),false);assert.equal(verifyApproval({...a,status:'pending'},p,'123'),false);
fs.appendFileSync(path.join(dir,'weather-fr.mp4'),'changed');assert.equal(verifyApproval(a,inspect(dir,d,null,n,fakeProbe),'123'),false);
fs.writeFileSync(path.join(dir,'weather-fr-male.mp4'),'extra');assert.throws(()=>inspect(dir,d,null,n,fakeProbe),/Unexpected package asset/);fs.unlinkSync(path.join(dir,'weather-fr-male.mp4'));
fs.unlinkSync(path.join(dir,'weather-fr.mp4'));assert.throws(()=>inspect(dir,d,null,n,fakeProbe),/Missing/);
assert.equal(allowed('../source.json'),false);
console.log('PASS V31: stale/changed reports, source restrictions, chronological frames, manifest checks, exact package digest, missing assets and approval binding (fixture media)');
}finally{fs.rmSync(dir,{recursive:true,force:true})}
const update=fs.readFileSync('.github/workflows/update.yml','utf8'),video=fs.readFileSync('.github/workflows/video.yml','utf8');
assert.match(update,/inputs\.approve_publication == true/);assert.match(update,/node v31-review\.cjs release/);assert.match(update,/cp -r _approved\/\. _site\/video\//);assert.doesNotMatch(update,/cp _video\/source\.json|workflow_run:/);assert.match(video,/node v31-review\.cjs draft video-output/);assert.match(video,/Inside-Mauritius-V31-Reviewed-Draft/);
console.log('PASS V31: workflow guard configuration');
