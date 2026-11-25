'use strict';
// V31: technical checks are not editorial approval. No network or writes in assess().
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),cp=require('node:child_process');
const {select}=require('./tracker.js');
const sizes={original:[2160,3840],'4k':[2160,3840],hd:[1080,1920],landscape:[1920,1080],landscape4k:[3840,2160]};
const voices=['fr','fr-male','mfe','mfe-male'];
const canonical=x=>JSON.stringify(x===undefined?null:x,(_k,v)=>v&&typeof v==='object'&&!Array.isArray(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,v[k]])):v);
const same=(a,b)=>canonical(a)===canonical(b);
const time=s=>typeof s==='string'&&/(Z|[+-]\d\d:\d\d)$/.test(s)?Date.parse(s):NaN;
const recent=(s,n,age)=>Number.isFinite(time(s))&&time(s)<=n+300000&&n-time(s)<=age;
const coords=p=>p&&Number.isFinite(p.lat)&&Number.isFinite(p.lon)&&p.lat>=-45&&p.lat<0&&p.lon>=30&&p.lon<=90;
const noStorm=p=>p==null||same(p,{});
const sourceURL=s=>{try{const u=new URL(s);return u.protocol==='https:'&&u.hostname==='metservice.intnet.mu'&&!u.port&&!u.username&&!u.password&&u.pathname.startsWith('/mmsimages/')&&/\.(jpg|jpeg|png|webp)$/i.test(u.pathname)}catch{return false}};
function assess(m,d,f,n=Date.now()){
 const errors=[];const need=(v,msg)=>{if(!v)errors.push(msg)};
 if(!m||!d)return ['Missing report or official observation'];
 need(m.preview_only===false&&m.publication_status==='review_required','Not a reviewable rendered report');
 need(d.source_status==='ok'&&recent(d.checked_at,n,2700000)&&Array.isArray(d.errors)&&d.errors.length===0,'Official observation unavailable or stale');
 need(m.source_status==='ok'&&recent(m.generated_at,n,5400000)&&recent(m.checked_at,time(m.generated_at),2700000)&&time(m.checked_at)<=time(m.generated_at)+300000,'Report or source timestamp stale or invalid');
 need(typeof d.warning==='string'&&/^(No warning reported|Class (I|II|III|IV))$/.test(d.warning)&&m.warning===d.warning,'Official warning missing, changed or not verified');
 need((noStorm(d.storm)&&noStorm(m.observation))||(coords(d.storm)&&typeof d.storm.observed==='string'&&d.storm.observed.trim()&&same(m.observation,d.storm)),'Observation or coordinates changed/unverified');
 const b=select(d,f,n);
 need(same(m.official_forecast??null,b??null),'Official forecast changed or cannot be matched');
 const t=m.satellite_frame_times;
 need(sourceURL(m.satellite_url)&&Array.isArray(t)&&t.length>0&&t.length===m.satellite_frame_count&&t.length<=24&&t.every((x,i)=>recent(x,n,86400000)&&time(x)<=n&&time(x)<=time(m.generated_at)+300000&&(!i||time(x)>time(t[i-1])))&&recent(t.at(-1),n,21600000),'Satellite imagery missing, stale or invalid');
 need(typeof m.observation_key==='string'&&/^[a-f0-9]{64}$/.test(m.observation_key)&&typeof m.report_key==='string'&&/^[a-f0-9]{64}$/.test(m.report_key),'Report identity missing');
 const v=Object.keys(m.videos||{});
 need(v.includes('fr')&&v.includes('mfe')&&v.every(x=>voices.includes(x)),'Required rendered voices missing or unexpected');
 for(const voice of v){
  need(m.videos[voice]==='weather-'+voice+'.mp4','Unexpected report filename');
  for(const [fmt,[w,h]] of Object.entries(sizes)){
   const filename='weather-'+voice+(fmt==='original'?'':'-'+fmt)+'.mp4',q=m.quality_checks?.[voice]?.[fmt];
   need(m.formats?.[voice]?.[fmt]===filename&&q?.width===w&&q?.height===h&&q?.audio===true&&q?.caption_check===true&&Number.isFinite(q.av_delta)&&q.av_delta>=0&&q.av_delta<.20,'Invalid video manifest: '+filename);
  }
 }
 return errors;
}
function allowed(name){return /^(source\.json|weather-(fr|mfe)(-male)?(-4k|-hd|-landscape|-landscape4k)?\.mp4|voice-(fr|mfe)(-male)?\.mp3|narration-(fr|mfe)\.txt|captions-(fr|mfe)(-male)?\.vtt|poster-(fr|mfe)-4k\.png|satellite-fullscreen(-forecast)?-4k\.mp4)$/.test(name)}
function hashes(dir){
 const out={};for(const n of fs.readdirSync(dir).sort()){
  if(!allowed(n))continue;
  const p=path.join(dir,n),s=fs.lstatSync(p);
  if(!s.isFile()||s.size<1)throw Error('Invalid package file: '+n);
  const h=crypto.createHash('sha256'),fd=fs.openSync(p,'r');try{const b=Buffer.alloc(1024*1024);let k;while((k=fs.readSync(fd,b,0,b.length,null))>0)h.update(b.subarray(0,k))}finally{fs.closeSync(fd)}out[n]=h.digest('hex')
 }return out
}
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
function probe(file,w,h,audio,subtitles=false){const p=JSON.parse(cp.execFileSync('ffprobe',['-v','error','-show_streams','-of','json',file],{encoding:'utf8',timeout:30000,maxBuffer:2e6}));const v=p.streams.find(x=>x.codec_type==='video'),a=p.streams.find(x=>x.codec_type==='audio');if(v?.width!==w||v?.height!==h||!(Number(v.duration)>0)||audio&&(!a||!(Number(a.duration)>0)||Math.abs(Number(v.duration)-Number(a.duration))>=.20)||subtitles&&!p.streams.some(x=>x.codec_type==='subtitle'))throw Error('Media probe failed: '+path.basename(file))}
function inspect(dir,d,f,now=Date.now(),probeFn=probe){
 const m=read(path.join(dir,'source.json')),errors=assess(m,d,f,now);if(errors.length)throw Error(errors.join('; '));
 const files=hashes(dir),expected=new Set(['source.json']);
 for(const voice of Object.keys(m.videos)){
  for(const [fmt,[w,h]] of Object.entries(sizes)){const name=m.formats[voice][fmt];expected.add(name);if(!files[name])throw Error('Missing '+name);probeFn(path.join(dir,name),w,h,true,fmt==='original')}
  for(const [key,prefix,ext] of [['previews','voice','.mp3'],['captions','captions','.vtt']]){const name=prefix+'-'+voice+ext;expected.add(name);if(m[key]?.[voice]!==name||!files[name])throw Error('Missing '+name)}
  expected.add('narration-'+voice.split('-')[0]+'.txt');if(!files['narration-'+voice.split('-')[0]+'.txt'])throw Error('Missing narration');
 }
 for(const [key,name] of [['premium_satellite_fullscreen','satellite-fullscreen-4k.mp4'],['premium_satellite_forecast','satellite-fullscreen-forecast-4k.mp4']]){
  if(m[key]!=null){expected.add(name);if(m[key]!==name||!files[name]||m.premium_satellite_publication_status!=='review_required'||m.geographic_satellite_overlay?.source!=='https://view.eumetsat.int/geoserver/wms'||m.geographic_satellite_overlay?.status!=='ok')throw Error('Invalid premium asset');probeFn(path.join(dir,name),3840,2160,false)}
  else if(files[name])throw Error('Unexpected premium asset');
 }
 for(const [voice,name] of Object.entries(m.posters||{})){expected.add(name);if(!['fr','mfe'].includes(voice)||name!=='poster-'+voice+'-4k.png'||!files[name]||m.poster_publication_status!=='review_required')throw Error('Invalid poster')}
 for(const name of Object.keys(files))if(!expected.has(name))throw Error('Unexpected package asset: '+name);
 return {manifest_sha256:files['source.json'],package_sha256:crypto.createHash('sha256').update(canonical(files)).digest('hex'),files,report_key:m.report_key,generated_at:m.generated_at}
}
function verifyApproval(a,p,run){
 return a?.schema===1&&a.status==='approved'&&String(a.run_id)===String(run)&&typeof a.approved_by==='string'&&a.approved_by.length>0&&Number.isFinite(time(a.approved_at))&&a.package_sha256===p.package_sha256&&a.generated_at===p.generated_at&&a.report_key===p.report_key&&a.manifest_sha256===p.manifest_sha256&&same(a.files,p.files)
}
function cli(){const [mode,dir,run,receipt]=process.argv.slice(2);const d=read('data.json');let f=null;try{f=read('official-forecast.json')}catch{}const p=inspect(dir,d,f);if(mode==='draft'){const summary='Technical validation passed; editorial approval required.\n\nDraft run: '+(process.env.GITHUB_RUN_ID||'local')+'\n\nPackage SHA-256: `'+p.package_sha256+'`\n\nReview the exact video, warning, image dates, audio and captions before approval.\n';console.log(summary);if(process.env.GITHUB_STEP_SUMMARY)fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,summary);return}if(!/^\d+$/.test(run||'')||!receipt)throw Error('Missing run or receipt');if(mode==='approve'){if(process.env.GITHUB_EVENT_NAME!=='workflow_dispatch'||process.env.GITHUB_REF!=='refs/heads/main'||!process.env.GITHUB_ACTOR)throw Error('Authenticated main-branch manual approval required');if(process.env.APPROVED_PACKAGE_SHA!==p.package_sha256)throw Error('Reviewed package digest does not match');fs.writeFileSync(receipt,JSON.stringify({schema:1,status:'approved',run_id:run,approved_by:process.env.GITHUB_ACTOR,approved_at:new Date().toISOString(),...p},null,2)+'\n');return}if(mode==='release'){const a=read(receipt);if(!verifyApproval(a,p,run))throw Error('Approval does not match exact report bytes');const dest=process.argv[6];if(!dest)throw Error('Missing stage directory');fs.mkdirSync(dest,{recursive:true});for(const name of Object.keys(p.files))fs.copyFileSync(path.join(dir,name),path.join(dest,name));fs.writeFileSync(path.join(dest,'publication.json'),JSON.stringify({status:'approved',generated_at:p.generated_at,approved_at:a.approved_at,package_sha256:p.package_sha256},null,2));console.log('Approved package verified');return}throw Error('Unknown mode')}
if(require.main===module){try{cli()}catch(e){console.error('V31 blocked:',e.message);process.exitCode=1}}
module.exports={assess,allowed,verifyApproval,inspect,probe};
