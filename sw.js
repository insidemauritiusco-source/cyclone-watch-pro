const CACHE='cyclone-v9-professional-voice-shell';const SHELL=['./','index.html','v6.js','v6.css','v7.js','v7.css','v8.js','v8.css','v9.js','v9.css','video-player.js','studio-logo.png','manifest.webmanifest','icon.svg'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('cyclone-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{const u=new URL(e.request.url);if(e.request.method!=='GET'||u.origin!==self.location.origin||!u.href.startsWith(self.registration.scope)||(u.pathname.endsWith('/data.json')||u.pathname.endsWith('/media.json')||u.pathname.endsWith('/archive.json')))return;
if(e.request.mode==='navigate'){e.respondWith(fetch(e.request).catch(()=>caches.match('index.html')));return}
if(SHELL.some(s=>u.href===new URL(s,self.registration.scope).href)){e.respondWith(fetch(e.request).then(r=>{if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy))}return r}).catch(()=>caches.match(e.request)))}
});
self.addEventListener('notificationclick',e=>{e.notification.close();e.waitUntil(self.clients.openWindow(self.registration.scope))});