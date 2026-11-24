(()=>{'use strict';const $=id=>document.getElementById(id);let meta=null;
function show(){const v=$('weatherVideo'),a=$('videoDownload'),s=$('videoState'),l=$('videoLanguage').value;const f=meta?.videos?.[l];if(f!==('weather-'+l+'.mp4')){v.pause();v.removeAttribute('src');v.load();v.hidden=true;a.hidden=true;s.textContent='Video not published yet. Open the video workflow and refresh after deployment.';return}
const id=encodeURIComponent(meta.generated_at||meta.checked_at||'');const url='video/'+f+'?v='+id;v.pause();v.src=url;v.hidden=false;a.href=url;a.download='Inside-Mauritius-Cyclone-4K-'+l+'.mp4';a.hidden=false;s.textContent='Dated report: '+(meta.observation?.observed||'observation unavailable')+' · generated '+(meta.generated_at||'unknown')+' · '+(meta.satellite_capture?'Satellite capture '+meta.satellite_capture:'Satellite unavailable — schematic map')+' · '+(meta.voice?.[l]||'Synthetic narration')+' · '+(meta.satellite_frame_count||0)+' verified satellite frame(s)';}
async function load(){try{const r=await fetch('video/source.json?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('video');meta=await r.json()}catch(e){meta=null}show()}
$('weatherVideo').onerror=()=>{$('videoState').textContent='Video playback unavailable on this device. Try the MP4 download.'};$('videoLanguage').onchange=()=>{clearAudio();show()};$('videoReload').onclick=()=>{clearAudio();load()};
const v=$('weatherVideo'),a=$('localAudio'),input=$('localVoice');let localURL=null;
function clearAudio(){a.pause();a.removeAttribute('src');if(localURL)URL.revokeObjectURL(localURL);localURL=null;v.muted=false;input.value='';$('clearLocalVoice').hidden=true}
input.onchange=()=>{const file=input.files?.[0];if(!file)return;clearAudio();localURL=URL.createObjectURL(file);a.src=localURL;v.pause();v.muted=true;$('clearLocalVoice').hidden=false;$('videoState').textContent+=' · Local narration preview (MP4 unchanged)'};
$('clearLocalVoice').onclick=clearAudio;
v.addEventListener('play',()=>{if(localURL){a.currentTime=v.currentTime;a.play().catch(()=>{})}});
for(const ev of ['pause','ended'])v.addEventListener(ev,()=>a.pause());
v.addEventListener('seeked',()=>{if(localURL&&Number.isFinite(a.duration))a.currentTime=Math.min(v.currentTime,a.duration)});
v.addEventListener('ratechange',()=>{if(localURL)a.playbackRate=v.playbackRate});
function scriptLink(){const l=$('videoLanguage').value;const link=$('voiceScript');link.href='video/narration-'+l+'.txt';link.download='cyclone-narration-'+l+'.txt';link.hidden=!meta?.videos?.[l]||!meta?.satellite_frame_times}
$('videoLanguage').addEventListener('change',scriptLink);$('videoReload').addEventListener('click',()=>setTimeout(scriptLink,2000));
load().then(scriptLink)})();