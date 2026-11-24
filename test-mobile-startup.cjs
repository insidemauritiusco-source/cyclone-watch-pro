const {chromium}=require('playwright'),http=require('node:http'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{const root=path.resolve('_site'),server=http.createServer((req,res)=>{let p=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);if(p===root)p=path.join(p,'index.html');if(!p.startsWith(root+path.sep)||!fs.existsSync(p)){res.writeHead(404);return res.end()}const types={'.html':'text/html','.json':'application/json','.js':'application/javascript','.css':'text/css','.png':'image/png','.svg':'image/svg+xml'};res.setHeader('Content-Type',types[path.extname(p)]||'application/octet-stream');fs.createReadStream(p).pipe(res)});await new Promise(r=>server.listen(0,'127.0.0.1',r));let browser;try{
browser=await chromium.launch({channel:'chrome',headless:true,args:['--no-sandbox']});const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,serviceWorkers:'block'});
// External imagery and maps are deliberately unavailable in this smoke test; local controls must still work.
await page.route('**/*',route=>route.request().url().startsWith('http://127.0.0.1:')?route.continue():route.abort());
await page.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>window.cycloneStartup?.loaded?.length+window.cycloneStartup?.errors?.length===16);
const result=await page.evaluate(()=>({startup:window.cycloneStartup,hero:getComputedStyle(document.getElementById('v15Stage')).display,clock:document.getElementById('clock').textContent,controls:!!document.getElementById('v24Live').onclick}));
assert.deepEqual(result.startup.errors,[]);assert.equal(result.startup.loaded.length,16);assert.equal(result.hero,'grid');assert.ok(result.controls);
const ui=await page.evaluate(()=>({nav:document.querySelectorAll('.deskquick a').length,targets:[...document.querySelectorAll('.deskquick a')].every(a=>!!document.querySelector(a.hash)),metrics:getComputedStyle(document.querySelector('.v151metrics')).gridTemplateColumns.split(' ').length,icon:getComputedStyle(document.querySelector('.v151dock svg')).width}));assert.equal(ui.nav,4);assert.equal(ui.targets,true);assert.equal(ui.metrics,4);assert.equal(ui.icon,'22px');
const brand=await page.evaluate(()=>({tag:document.querySelector('meta[name=cyclone-build]').content,header:document.querySelector('.v25brandname').textContent,afterMap:!!(document.getElementById('v15Track').compareDocumentPosition(document.querySelector('.v151dock'))&Node.DOCUMENT_POSITION_FOLLOWING),beforeAdvanced:!!(document.querySelector('.v151dock').compareDocumentPosition(document.getElementById('v16Weather'))&Node.DOCUMENT_POSITION_FOLLOWING),overflow:document.documentElement.scrollWidth>innerWidth+2}));assert.equal(brand.tag,'v25.1-reference-layout');assert.equal(brand.header,'Inside Mauritius');assert.ok(!brand.afterMap&&brand.beforeAdvanced);assert.equal(brand.overflow,false);
const ref=await page.evaluate(()=>({buttons:[...document.querySelectorAll('.reference-nav button')].map(x=>x.id),navBeforeSatellite:!!(document.querySelector('.reference-nav').compareDocumentPosition(document.getElementById('v15Satellite'))&Node.DOCUMENT_POSITION_FOLLOWING),forecast:typeof document.getElementById('referenceForecast').onclick,legend:document.querySelectorAll('.reference-legend span').length}));assert.deepEqual(ref.buttons,['v151-official','v151-satellite','v151-animation','referenceForecast','v151-alerts']);assert.ok(ref.navBeforeSatellite);assert.equal(ref.forecast,'function');assert.equal(ref.legend,5);console.log('PASS V25.1 reference layout: five top controls, four compact metrics, map key, no mobile horizontal overflow');
assert.equal(await page.locator('#officialForecastToggle').count(),1);await page.waitForFunction(()=>!document.getElementById('officialForecastStatus').textContent.startsWith('Checking'));await page.waitForFunction(()=>document.getElementById('clock').textContent.length>0);
await page.waitForFunction(()=>document.getElementById('v15MediaBadge').textContent!=='Checking source...');
await page.waitForFunction(()=>document.getElementById('islandGrid').children.length>=3);
await page.waitForFunction(()=>document.getElementById('pressureChart').children.length>0);
console.log('PASS V24.1 mobile browser startup, satellite status, island grid and chart rendering (external sources blocked in test)');
// Use explicitly synthetic test-only responses to test playback independently of the external feed.
const now=Date.now(),iso=t=>new Date(t).toISOString(),issued=now-3600000;
const obs={name:'Tropical Depression (B03)',observed:iso(now-1800000),lat:-9.7,lon:76.8,pressure:1003,speed:12,direction:'South Southwest',wind:null};
const testData={source_status:'ok',checked_at:iso(now),warning:'No warning reported',storm:obs,history:[obs]};
const testBulletin={system_number:3,bulletin_number:1,issued_at:iso(issued),anchor:{lat:-9.5,lon:77.1},points:[{hours:12,valid_at:iso(issued+12*3600000),lat:-10.5,lon:76.4,max_wind_kt:30,classification:'TROPICAL DEPRESSION'},{hours:24,valid_at:iso(issued+24*3600000),lat:-11.4,lon:75.8}]};
const testFeed={schema:1,issuer:'Meteo-France RSMC La Reunion',source:'https://wwmiws.wmo.int/index.php/metareas/bulletinset/8S/html',checked_at:iso(now),status:'ok',bulletins:[testBulletin]};
await page.route('**/data.json?*',r=>r.fulfill({json:testData}));
await page.route('**/official-forecast.json?*',r=>r.fulfill({json:testFeed}));
await page.reload({waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>!document.getElementById('forecastPlay').disabled&&!!document.getElementById('forecastSelectedPoint'));
const arrow=await page.locator('#mmsMovementArrow').getAttribute('transform');assert.ok(arrow.includes('rotate(202.5)'));
assert.match(await page.locator('#forecastDetail').textContent(),/30 kt/);
await page.locator('#forecastRate').selectOption('600');
await page.locator('#forecastPlay').click();
await page.waitForFunction(()=>document.getElementById('forecastStep').textContent.includes('+24h'));
assert.match(await page.locator('#forecastDetail').textContent(),/Not reported/);
assert.equal(await page.locator('#mmsMovementArrow').getAttribute('transform'),arrow);
assert.equal(await page.locator('#officialForecastTrack line').count(),2);
await page.locator('#forecastReplay').click();
await page.waitForFunction(()=>document.getElementById('forecastStep').textContent.includes('+12h'));
await page.locator('#officialForecastToggle').uncheck();
assert.equal(await page.locator('#officialForecastTrack line').count(),0);
assert.equal(await page.locator('#forecastPlay').isDisabled(),true);
console.log('PASS forecast playback browser fixture: dated points, reported wind, replay, toggle, unchanged movement arrow');
// Browser-only synthetic media fixture, kept outside the deployed site.
const os=require('node:os'),cp=require('node:child_process');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'premium-test-')),clip=path.join(temp,'fixture.mp4');
try{
cp.execFileSync('ffmpeg',['-v','error','-f','lavfi','-i','color=c=navy:s=3840x2160:r=5:d=8','-c:v','libx264','-threads','2','-preset','ultrafast','-pix_fmt','yuv420p','-movflags','+faststart',clip]);
let manifest={preview_only:false,publication_status:'review_required',premium_satellite_publication_status:'review_required',premium_satellite_fullscreen:'satellite-fullscreen-4k.mp4',generated_at:iso(now),observation_key:'TEST',geographic_satellite_overlay:{status:'ok',source:'https://view.eumetsat.int/geoserver/wms',crs:'EPSG:4326',credit:'TEST ONLY',frames:[iso(now-7200000),iso(now-3600000)].map(captured_at=>({captured_at,sha256:{wide:'a'.repeat(64)}}))}};
for(const desktop of [false,true]){
 const ctx=await browser.newContext({viewport:desktop?{width:1366,height:768}:{width:390,height:844},isMobile:!desktop,hasTouch:!desktop,serviceWorkers:'block',acceptDownloads:true});
 const p=await ctx.newPage();
 await p.route('**/*',r=>r.request().url().startsWith('http://127.0.0.1:')?r.continue():r.abort());
 await p.route('**/video/source.json?*',r=>r.fulfill({json:manifest}));
 await p.route('**/video/satellite-fullscreen-4k.mp4?*',r=>r.fulfill({path:clip,contentType:'video/mp4'}));
 await p.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'domcontentloaded'});
 await p.waitForFunction(()=>!document.getElementById('premiumPlay').disabled);
 assert.equal(await p.locator('#premiumVideo').evaluate(v=>v.videoWidth),3840);
 assert.match(await p.locator('#premiumDates').textContent(),/UTC.*MUT/);
 assert.equal(await p.locator('#premiumApproved').isDisabled(),true);
 await p.locator('#premiumPlay').click();await p.waitForFunction(()=>!document.getElementById('premiumVideo').paused);
 await p.locator('#premiumLoop').uncheck();assert.equal(await p.locator('#premiumVideo').evaluate(v=>v.loop),false);
 await p.locator('#premiumLoop').check();assert.equal(await p.locator('#premiumVideo').evaluate(v=>v.loop),true);
 await p.locator('#premiumReplay').click();
 await p.waitForFunction(()=>!document.getElementById('premiumVideo').paused||document.getElementById('premiumVideo').ended);
 // Check fullscreen invocation without depending on headless OS support.
 await p.locator('#premiumVideo').evaluate(v=>{v.requestFullscreen=()=>{v.dataset.fullTest='yes';return Promise.resolve()}});
 await p.locator('#premiumFull').click();assert.equal(await p.locator('#premiumVideo').getAttribute('data-full-test'),'yes');
 for(const id of ['premiumCheckDates','premiumCheckWarning','premiumCheckMedia','premiumApprove'])await p.locator('#'+id).check();
 assert.equal(await p.locator('#premiumApproved').isDisabled(),false);
 assert.equal(await p.locator('#approvedDownload').isDisabled(),true);
 const dl=p.waitForEvent('download');await p.locator('#premiumApproved').click();assert.equal((await dl).suggestedFilename(),'Inside-Mauritius-approved-satellite-4k.mp4');
 manifest={...manifest,generated_at:iso(Date.parse(manifest.generated_at)+1000)};
 await p.locator('#premiumApproved').click();
 await p.waitForFunction(()=>document.getElementById('premiumReview').textContent.includes('changed'));
 assert.equal(await p.locator('#premiumApproved').isDisabled(),true);
 await p.locator('#premiumRefresh').click();await p.waitForFunction(()=>!document.getElementById('premiumPlay').disabled);
 assert.equal(await p.locator('#premiumApprove').isChecked(),false);
 assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false);
 await ctx.close();
}
console.log('PASS Premium player browser: mobile and desktop 4K metadata, play/replay, fullscreen request, independent approval, changed-version rejection and refresh');
}finally{fs.rmSync(temp,{recursive:true,force:true})}
}finally{if(browser)await browser.close();server.close()}})().catch(e=>{console.error(e);process.exitCode=1});
