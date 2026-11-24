(()=>{'use strict';const $=id=>document.getElementById(id),v=$('weatherVideo'),a=$('localAudio'),sample=$('voiceSample'),input=$('localVoice');let meta=null,localURL=null;
const code=()=>$('videoLanguage').value;
const token=()=>encodeURIComponent(meta?.generated_at||meta?.checked_at||'');
const media=f=>'video/'+f+'?v='+token();
function clearAudio(){a.pause();a.removeAttribute('src');if(localURL)URL.revokeObjectURL(localURL);localURL=null;v.muted=false;input.value='';$('clearLocalVoice').hidden=true}
function stopSample(){sample.pause();sample.removeAttribute('src');sample.hidden=true}
function settings(){const speed=+$('voiceSpeed').value,volume=+$('voiceVolume').value;for(const el of [v,a,sample]){el.playbackRate=speed;el.volume=volume}}
function cc(){for(const t of v.textTracks)t.mode=$('voiceCC').checked&&!localURL?'showing':'disabled'}
function show(){clearAudio();stopSample();const l=code(),f=meta?.videos?.[l],d=$('videoDownload'),s=$('videoState');v.pause();v.querySelectorAll('track').forEach(t=>t.remove());const available=f==='weather-'+l+'.mp4';$('listenVoice').disabled=meta?.previews?.[l]!=='voice-'+l+'.mp3';$('voiceScript').hidden=!meta?.videos?.[l];$('voiceScript').href=media('narration-'+(l.startsWith('mfe')?'mfe':'fr')+'.txt');$('voiceScript').download='cyclone-narration.txt';
if(!available){v.removeAttribute('src');v.load();v.hidden=true;d.hidden=true;s.textContent='Selected voice not published yet. Choose an available voice or run the video workflow.';return}
v.src=media(f);v.hidden=false;d.href=media(f);d.download='Inside-Mauritius-Cyclone-4K-'+l+'.mp4';d.hidden=false;
if(meta?.captions?.[l]==='captions-'+l+'.vtt'){const t=document.createElement('track');t.kind='captions';t.label=l.startsWith('mfe')?'Kreol Morisien':'Français';t.srclang=l.startsWith('mfe')?'mfe':'fr';t.src=media(meta.captions[l]);t.default=$('voiceCC').checked;t.addEventListener('load',cc);v.append(t)}settings();cc();
s.textContent='Dated report: '+(meta.observation?.observed||'observation unavailable')+' · generated '+(meta.generated_at||'unknown')+' · '+(meta.satellite_capture?'Satellite capture '+meta.satellite_capture:'Satellite unavailable — schematic map')+' · '+(meta.voice?.[l]||'Synthetic narration')+' · '+(meta.satellite_frame_count||0)+' verified satellite frame(s)';}
async function load(){try{const r=await fetch('video/source.json?t='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('video');meta=await r.json()}catch(e){meta=null}show()}
$('listenVoice').onclick=()=>{const l=code();if(meta?.previews?.[l]!=='voice-'+l+'.mp3')return;v.pause();sample.src=media(meta.previews[l]);sample.hidden=false;settings();sample.play().catch(()=>{})};
$('weatherVideo').onerror=()=>{$('videoState').textContent='Video playback unavailable on this device. Try the MP4 download.'};$('videoLanguage').onchange=show;$('videoReload').onclick=load;$('voiceSpeed').onchange=settings;$('voiceVolume').oninput=settings;$('voiceCC').onchange=cc;
input.onchange=()=>{const file=input.files?.[0];if(!file)return;clearAudio();localURL=URL.createObjectURL(file);a.src=localURL;v.pause();stopSample();v.muted=true;$('clearLocalVoice').hidden=false;settings();cc();$('videoState').textContent+=' · Local narration preview (published MP4 unchanged; original captions disabled)'};
$('clearLocalVoice').onclick=()=>{clearAudio();cc()};
v.addEventListener('play',()=>{sample.pause();if(localURL){a.currentTime=v.currentTime;a.play().catch(()=>{})}});
for(const ev of ['pause','ended'])v.addEventListener(ev,()=>a.pause());
v.addEventListener('seeked',()=>{if(localURL&&Number.isFinite(a.duration))a.currentTime=Math.min(v.currentTime,a.duration)});
v.addEventListener('ratechange',()=>{if(localURL)a.playbackRate=v.playbackRate});v.addEventListener('loadedmetadata',()=>{settings();cc()});load()})();