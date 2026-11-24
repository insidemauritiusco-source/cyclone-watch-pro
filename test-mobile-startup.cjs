const {chromium}=require('playwright'),http=require('node:http'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{const root=path.resolve('_site'),server=http.createServer((req,res)=>{let p=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);if(p===root)p=path.join(p,'index.html');if(!p.startsWith(root+path.sep)||!fs.existsSync(p)){res.writeHead(404);return res.end()}const types={'.html':'text/html','.json':'application/json','.js':'application/javascript','.css':'text/css','.png':'image/png','.svg':'image/svg+xml'};res.setHeader('Content-Type',types[path.extname(p)]||'application/octet-stream');fs.createReadStream(p).pipe(res)});await new Promise(r=>server.listen(0,'127.0.0.1',r));let browser;try{
browser=await chromium.launch({channel:'chrome',headless:true,args:['--no-sandbox']});const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,serviceWorkers:'block'});
// External imagery and maps are deliberately unavailable in this smoke test; local controls must still work.
await page.route('**/*',route=>route.request().url().startsWith('http://127.0.0.1:')?route.continue():route.abort());
await page.goto('http://127.0.0.1:'+server.address().port+'/',{waitUntil:'domcontentloaded'});
await page.waitForFunction(()=>window.cycloneStartup?.loaded?.length+window.cycloneStartup?.errors?.length===14);
const result=await page.evaluate(()=>({startup:window.cycloneStartup,hero:getComputedStyle(document.getElementById('v15Stage')).display,clock:document.getElementById('clock').textContent,controls:!!document.getElementById('v24Live').onclick}));
assert.deepEqual(result.startup.errors,[]);assert.equal(result.startup.loaded.length,14);assert.equal(result.hero,'grid');assert.ok(result.controls);
await page.waitForFunction(()=>document.getElementById('clock').textContent.length>0);
await page.waitForFunction(()=>document.getElementById('v15MediaBadge').textContent!=='Checking source...');
await page.waitForFunction(()=>document.getElementById('islandGrid').children.length>=3);
await page.waitForFunction(()=>document.getElementById('pressureChart').children.length>0);
console.log('PASS V24.1 mobile browser startup, satellite status, island grid and chart rendering (external sources blocked in test)');
}finally{if(browser)await browser.close();server.close()}})().catch(e=>{console.error(e);process.exitCode=1});
