"""Render a dated independent weather video; never synthesize satellite imagery."""
import json, datetime as dt, pathlib, math, re, subprocess, urllib.request, urllib.parse, textwrap
from PIL import Image, ImageDraw, ImageFont, ImageOps
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/'video-output'; OUT.mkdir(exist_ok=True)
D=json.loads((ROOT/'data.json').read_text()); S=D.get('storm') or {}
W,H=2160,3840
now=dt.datetime.now(dt.timezone.utc)
try:
    stamp=dt.datetime.fromisoformat(D['checked_at'])
    fresh=D.get('source_status')=='ok' and -300 <= (now-stamp).total_seconds() <= 2700
    checked=stamp.astimezone(dt.timezone(dt.timedelta(hours=4))).strftime('%d %b %Y, %H:%M MUT')
except Exception:
    fresh=False; checked='Unavailable'
def number(key,unit):
    v=S.get(key);return f'{v:g} {unit}' if isinstance(v,(float,int)) else '—'
def distance():
    try:
        lat,lon=float(S['lat']),float(S['lon']); r=math.pi/180
        a=math.sin((lat+20.2)*r/2)**2+math.cos(lat*r)*math.cos(20.2*r)*math.sin((lon-57.5)*r/2)**2
        return f'{round(12742*math.asin(math.sqrt(min(1,a)))):,} km'
    except Exception:return '—'
warning=D.get('warning','Unknown') if fresh else 'Current warning not verified'
warn_fr={'No warning reported':'Aucun avertissement signalé'}.get(warning,warning.replace('Class ','Classe ') if warning.startswith('Class ') else 'Avertissement actuel non vérifié')
name=S.get('name','Système non confirmé').replace('Tropical Disturbance','Perturbation tropicale').replace('Tropical Depression','Dépression tropicale').replace('Tropical Cyclone','Cyclone tropical')
obs=str(S.get('observed','Non disponible'))
direction=str(S.get('direction') or 'Non signalée')
direction={'South Southwest':'Sud-sud-ouest','South-southwest':'Sud-sud-ouest','South':'Sud','West':'Ouest','North':'Nord','East':'Est'}.get(direction,direction)
im=Image.new('RGB',(W,H),'#0a1526'); draw=ImageDraw.Draw(im)
fontroot=pathlib.Path('/usr/share/fonts/truetype/dejavu')
def font(n,b=False):return ImageFont.truetype(str(fontroot/('DejaVuSans-Bold.ttf' if b else 'DejaVuSans.ttf')),n*2)
def rect(box,color,r=0):
    b=tuple(int(i*2) for i in box);draw.rounded_rectangle(b,radius=r*2,fill=color) if r else draw.rectangle(b,fill=color)
def line(x,y,t,size=26,color='#e8f4fa',bold=False,maxw=970):
    t=str(t); f=font(size,bold)
    while size>13 and draw.textlength(t,font=f)>maxw*2:
        size-=1;f=font(size,bold)
    draw.text((x*2,y*2),t,font=f,fill=color)
rect((0,0,1080,12),'#42d9ee')
line(54,39,'INSIDE MAURITIUS  /  MÉTÉO',31,bold=True)
rect((54,106,1026,195),'#d6393c',9)
line(76,119,'VEILLE CYCLONIQUE',55,'white',True)
line(54,222,'SOURCE MMS CONSULTÉE' if fresh else 'DONNÉES NON VÉRIFIÉES',27,'#42d9ee' if fresh else '#ffc36b',True)
line(54,274,name,48,bold=True)
line(54,353,'Observation : '+obs,29,'#b9d6e0')
rect((54,418,1026,1095),'#102337',10)
sat=None; image_time=None; image_url=None; frame_images=[]
def fetch_frame(item):
    url=item['url']; p=urllib.parse.urlparse(url)
    if p.scheme!='https' or p.hostname!='metservice.intnet.mu' or not p.path.startswith('/mmsimages/'):raise ValueError('Unapproved source')
    capture=dt.datetime.fromisoformat(item['captured_at'])
    if capture.tzinfo is None or not -600<=(now-capture).total_seconds()<=86400:raise ValueError('Invalid capture time')
    req=urllib.request.Request(url,headers={'User-Agent':'InsideMauritiusCycloneWatch/1.0','Referer':'https://metservice.intnet.mu/satellite-imagery.php','Accept':'image/*'})
    with urllib.request.urlopen(req,timeout=12) as response:
        end=urllib.parse.urlparse(response.geturl())
        if end.scheme!='https' or end.hostname!='metservice.intnet.mu' or not end.path.startswith('/mmsimages/'):raise ValueError('Unexpected redirect')
        raw=response.read(15_000_001)
    if len(raw)>15_000_000:raise ValueError('Image too large')
    import io
    with Image.open(io.BytesIO(raw)) as src:
        if src.width*src.height>30_000_000:raise ValueError('Image dimensions too large')
        image=ImageOps.contain(src.convert('RGB'),(1900,1110),Image.Resampling.LANCZOS)
    return (capture,image,url)
try:
    m=json.loads((ROOT/'media.json').read_text())
    latest=m.get('satellite')
    if latest:
        frame_images.append(fetch_frame(latest))
        from concurrent.futures import ThreadPoolExecutor
        def attempt(item):
            try:return fetch_frame(item)
            except Exception as e:print('Animation frame unavailable:',str(e));return None
        with ThreadPoolExecutor(max_workers=3) as pool:
            extra=list(pool.map(attempt,[x for x in m.get('frames',[]) if x['url']!=latest['url']][-7:]))
        frame_images.extend(x for x in extra if x)
        frame_images=sorted({f[0]:f for f in frame_images}.values(),key=lambda f:f[0])
        capture,sat,image_url=frame_images[-1]
        image_time=capture.strftime('%d %b %Y %H:%M UTC')
except Exception as e:print('Satellite unavailable:',str(e))
if sat:
    im.paste(sat,((W-sat.width)//2, (465*2)+(1110-sat.height)//2))
    line(76,430,'IMAGE SATELLITE MMS / METEOSAT',24,'#b9d6e0',True)
    line(76,1032,'Image : '+image_time,25,'#b9d6e0',True)
    line(76,1064,'Image publiée, agrandie pour le format 4K.',19,'#b9d6e0')
else:
    line(76,455,'IMAGE SATELLITE NON DISPONIBLE',29,'#ffc36b',True)
    line(76,509,'Aucune image satellite inventée.',24,'#b9d6e0')
    # Show only schematic reported coordinates, explicitly labelled.
    def xy(lat,lon):return (100+(lon-43)/40*880,600+(-4-lat)/25*410)
    for lat in range(-5,-26,-5):
        x,y=xy(lat,43);draw.line((int(x*2),int(y*2),1960,int(y*2)),fill='#294558',width=2)
    for lon in range(45,81,5):
        x,y=xy(-4,lon);draw.line((int(x*2),int(y*2),int(x*2),2020),fill='#294558',width=2)
    for n,lat,lon in [('Maurice',-20.2,57.5),('Rodrigues',-19.71,63.42),('Agalega',-10.4,56.6),('Madagascar',-19.4,46.7)]:
        x,y=xy(lat,lon);draw.ellipse((x*2-6,y*2-6,x*2+6,y*2+6),fill='#b9d6e0');line(x+8,y-20,n,19)
    try:
        lat,lon=float(S['lat']),float(S['lon'])
        if -29<=lat<=-4 and 43<=lon<=83:
            x,y=xy(lat,lon);draw.ellipse((x*2-40,y*2-40,x*2+40,y*2+40),outline='#42d9ee',width=8)
    except Exception:pass
    line(76,1053,'CARTE SCHÉMATIQUE — POSITION OBSERVÉE',21,'#b9d6e0',True)
def card(x,y,label,val):
    rect((x,y,x+475,y+105),'#172c45',8);line(x+19,y+12,label,20,'#b9d6e0',True,maxw=430);line(x+19,y+48,val,36,'#42d9ee',True,maxw=430)
card(54,1119,'PRESSION CENTRALE',number('pressure','hPa'));card(551,1119,'VITESSE DE DÉPLACEMENT',number('speed','km/h'))
card(54,1240,'DISTANCE DE MAURICE',distance());card(551,1240,'DIRECTION',direction)
rect((54,1361,1026,1467),'#172c45',8)
try:coord=f"{abs(S['lat']):.1f}°{'S' if S['lat']<0 else 'N'}  ·  {abs(S['lon']):.1f}°{'E' if S['lon']>=0 else 'W'}"
except Exception:coord='—'
line(74,1373,'COORDONNÉES OBSERVÉES',20,'#b9d6e0',True);line(74,1410,coord,36,'#42d9ee',True)
rect((54,1484,1026,1597),'#392e25',8);line(74,1495,'AVERTISSEMENT À MAURICE',22,'#ffc36b',True);line(74,1541,warn_fr,33,'#ffc36b',True,maxw=930)
line(54,1620,'Source vérifiée : '+checked,25,'#b9d6e0')
line(54,1670,'Source : Mauritius Meteorological Services (MMS)',23,'#b9d6e0')
line(54,1710,'Suivi indépendant. Consultez les avertissements officiels.',24,'#b9d6e0')
line(54,1750,'Ni prévision, ni alerte officielle. Image et observation',22,'#b9d6e0')
line(54,1782,'peuvent avoir des heures différentes.',22,'#b9d6e0')
rect((0,1857,1080,1920),'#d6393c');line(54,1871,'mr.insidemauritius.com/cyclone/',30,'white',True)
poster=OUT/'weather-4k.png';im.save(poster)
# Real chronological frames, no motion interpolation. A small animated news strip is
# explicitly decorative, never a depiction of wind or projected motion.
import tempfile
TMP=pathlib.Path(tempfile.mkdtemp(prefix='weather-frames-'))
frames=[]
for i,(captured,frame,url) in enumerate(frame_images):
    shot=im.copy(); d=ImageDraw.Draw(shot)
    d.rectangle((112,924,2048,2048),fill='#102337')
    shot.paste(frame,((W-frame.width)//2,930+(1110-frame.height)//2))
    d.rectangle((112,2050,2048,2182),fill='#102337')
    d.text((152,2058),'Image : '+captured.strftime('%d %b %Y %H:%M UTC'),font=font(25,True),fill='#b9d6e0')
    d.text((152,2123),'Séquence observée · aucune interpolation' if len(frame_images)>1 else 'Image unique · aucune animation des nuages',font=font(20),fill='#b9d6e0')
    path=TMP/f'frame-{i:02d}.png';shot.save(path);frames.append(path)
if not frames:frames=[poster]
# A short sequence clip is looped under each narration. Source timestamps remain visible.
concat=TMP/'frames.txt'
concat.write_text(''.join("file '"+str(p)+"'\nduration 1.5\n" for p in frames)+"file '"+str(frames[-1])+"'\n")
motion=TMP/'motion.mp4'
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-vf',"fps=24,drawbox=x=0:y=0:w=iw:h=24:color=0x42d9ee:t=fill,format=yuv420p",'-c:v','libx264','-preset','ultrafast','-crf','23','-threads','4','-movflags','+faststart',str(motion)],check=True)
print('Timestamped satellite frames:',len(frame_images))
narration=f"Inside Mauritius, veille cyclonique. {name}. Observation : {obs}. "
if fresh:
    if S.get('pressure') is not None:narration+=f"Pression centrale, {S['pressure']} hectopascals. "
    if S.get('speed') is not None:narration+=f"Déplacement à {S['speed']} kilomètres par heure, direction {direction}. "
    narration+=f"À Maurice : {warn_fr}. "
else:narration+="Les conditions actuelles ne sont pas vérifiées. "
narration+=("Image satellite publiée par les services météorologiques. " if sat else "Image satellite indisponible. " )+"Suivez les avertissements officiels de la météo de Maurice."
(OUT/'narration-fr.txt').write_text(narration)
krname=(S.get('name') or 'Sistem pa konfirme').replace('Tropical Disturbance','Pertirbasion tropikal').replace('Tropical Depression','Depresion tropikal').replace('Tropical Cyclone','Siklon tropikal').replace('Moderate Tropical Storm','Tanpet tropikal modere').replace('Severe Tropical Storm','Tanpet tropikal for')
krdir={'South Southwest':'sid sid wes','South-southwest':'sid sid wes','South':'sid','West':'wes','North':'nor','East':'les'}.get(str(S.get('direction')),str(S.get('direction') or 'pa signale'))
krwarning='Okenn avertisman signale' if warning=='No warning reported' else warning.replace('Class ','Klas ') if warning.startswith('Class ') else 'Avertisman aktiel pa verifie'
kreol=f"Inside Mauritius, siveyans siklon. {krname}. Observasion: {obs}. "
if fresh:
    if S.get('pressure') is not None:kreol+=f"Presion santral, {S['pressure']} ekto paskal. "
    if S.get('speed') is not None:kreol+=f"Deplasman, {S['speed']} kilomet par er, direksion {krdir}. "
    kreol+=f"Pou Moris, {krwarning}. "
else:kreol+="Kondision aktiel pa verifie. "
kreol+=("Zimaz satelit pibliye par servis meteo. " if sat else "Zimaz satelit pa disponib. ")+"Swiv avertisman ofisiel servis meteo Moris."
# Normalize date/time and numeric speech; keep original display values on the video.
def spoken(text,code):
    months={'January':'zanvie' if code=='mfe' else 'janvier','February':'fevriye' if code=='mfe' else 'février','March':'mars','April':'avril','May':'me' if code=='mfe' else 'mai','June':'zin' if code=='mfe' else 'juin','July':'zilye' if code=='mfe' else 'juillet','August':'out' if code=='mfe' else 'août','September':'septam' if code=='mfe' else 'septembre','October':'oktob' if code=='mfe' else 'octobre','November':'novam' if code=='mfe' else 'novembre','December':'desam' if code=='mfe' else 'décembre'}
    for a,z in months.items():text=re.sub(r'\b'+a+r'\b',z,text,flags=re.I)
    text=re.sub(r'\b0?(\d{1,2})\s*AM\b',lambda m:m.group(1)+(' er gramatin' if code=='mfe' else ' heures du matin'),text,flags=re.I)
    text=re.sub(r'\b(\d+)\.0\b',r'\1',text)
    text=re.sub(r'\bB0?(\d+)\b',r'B \1',text)
    return text
narration=spoken(narration,'fr');kreol=spoken(kreol,'mfe')
(OUT/'narration-fr.txt').write_text(narration)
(OUT/'narration-mfe.txt').write_text(kreol)
voices={}
# Prefer a licensed neural French model, with transparent fallback. Kreol remains
# an approximation until a native-language engine or reviewed recording is supplied.
def speak(code,script,audio):
    model=ROOT/'voice-model'/'fr_FR-siwis-medium.onnx'
    if model.exists():
        try:
            subprocess.run(['python','-m','piper','--model',str(model),'--output_file',str(audio)],input=script,text=True,check=True,timeout=120)
            return 'Piper SIWIS neural French (CC BY 4.0)' if code=='fr' else 'Kreol script / Piper French neural approximation; review pronunciation'
        except Exception as e:print('Neural voice unavailable:',str(e))
    subprocess.run(['espeak-ng','-v','fr','-s','140' if code=='mfe' else '150','-w',str(audio),script],check=True)
    return 'French synthetic fallback' if code=='fr' else 'Kreol script / French synthetic fallback; review pronunciation'
for code,script in [('fr',narration),('mfe',kreol)]:
    audio=OUT/f'voice-{code}.wav'
    voices[code]=speak(code,script,audio)
    video=OUT/f'weather-{code}.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-stream_loop','-1','-i',str(motion),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-af','highpass=f=70,alimiter=limit=0.9','-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',str(video)],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(video)]))
    assert any(x.get('codec_type')=='video' and x.get('width')==2160 and x.get('height')==3840 for x in probe['streams'])
    assert any(x.get('codec_type')=='audio' for x in probe['streams'])
(OUT/'source.json').write_text(json.dumps({'observation':S,'checked_at':D.get('checked_at'),'warning':warning,'source_status':D.get('source_status'),'satellite_url':image_url,'satellite_capture':image_time,'generated_at':now.isoformat(),'video_resolution':'2160x3840','voice':voices,'satellite_frame_count':len(frame_images),'satellite_frame_times':[f[0].isoformat() for f in frame_images],'voice_attribution':'SIWIS French Speech Synthesis Database / Piper SIWIS, CC BY 4.0 (when neural voice used)','videos':{'fr':'weather-fr.mp4','mfe':'weather-mfe.mp4'}},indent=2,ensure_ascii=False))
print('Videos rendered. Satellite included:',bool(sat))
