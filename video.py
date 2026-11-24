"""Render a dated independent weather video; never synthesize satellite imagery."""
import json, datetime as dt, pathlib, math, re, subprocess, urllib.request, urllib.parse, textwrap, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageOps
ROOT=pathlib.Path(__file__).resolve().parent
OUT=ROOT/'video-output'; OUT.mkdir(exist_ok=True)
D=json.loads((ROOT/'data.json').read_text()); S=D.get('storm') or {}
W,H=2160,3840
PREVIEW='--preview-only' in sys.argv
FRENCH_LENGTH=os.getenv('FRENCH_LENGTH','long')
if FRENCH_LENGTH not in ('long','short'):raise ValueError('Invalid report length')
from broadcast_gate import fingerprint, report_key
from forecast_video import load_forecast, forecast_words, zoom_scene_holds
from tv_layout import render_card, logo_transparent, ass_captions, observed_track
from geo_satellite import build as build_geo_satellite
GRAPHIC=os.getenv('GRAPHIC_LANGUAGE','auto')
LOGO=os.getenv('BROADCAST_LOGO','off')=='on'
if GRAPHIC not in ('auto','fr','mfe'):raise ValueError('Invalid graphic language')
SPEED=float(os.getenv('VOICE_SPEED','1.0'))
VOLUME=float(os.getenv('VOICE_VOLUME','1.0'))
if not 0.85<=SPEED<=1.15 or not 0.5<=VOLUME<=1.25:raise ValueError('Voice settings out of range')
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
FORECAST=load_forecast(D,ROOT,now)
print('Verified video forecast:',len(FORECAST['points']) if FORECAST else 0,'published points')
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
        image=ImageOps.contain(src.convert('RGB'),(1984,1400),Image.Resampling.LANCZOS)
    return (capture,image,url)
try:
    m=json.loads((ROOT/'media.json').read_text())
    latest=m.get('satellite')
    items={x['url']:x for x in m.get('frames',[]) if isinstance(x,dict) and x.get('url')}
    if latest:items[latest['url']]=latest
    from concurrent.futures import ThreadPoolExecutor
    def attempt(item):
        try:return fetch_frame(item)
        except Exception as e:print('Animation frame unavailable:',str(e));return None
    # Bound report size while spanning the available period rather than just the latest frames.
    ordered=sorted(items.values(),key=lambda x:x['captured_at'])
    if len(ordered)>12:
        ordered=[ordered[round(i*(len(ordered)-1)/11)] for i in range(12)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        frame_images=[x for x in pool.map(attempt,ordered) if x]
    frame_images=sorted({f[0]:f for f in frame_images}.values(),key=lambda f:f[0])
    if frame_images:
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
import tempfile
TMP=pathlib.Path(tempfile.mkdtemp(prefix='weather-frames-'))
motions={}; posters={}
GEO,GEO_IMAGES=build_geo_satellite(D,FORECAST,now) if not PREVIEW else ({'status':'skipped_preview','frames':[]},{})
print('Geographic satellite overlay:',GEO['status'],len(GEO['frames']), 'dated frames',GEO.get('reason') or '')
def satellite_map(zoom,step,total):
    if not GEO_IMAGES:return None
    keys=list(GEO_IMAGES);key=keys[round(step*(len(keys)-1)/max(1,total-1))];mode='close' if zoom else 'wide'
    return {'bounds':tuple(GEO['bounds'][mode]),'image':GEO_IMAGES[key][mode],'captured':dt.datetime.fromisoformat(key).strftime('%d/%m/%Y %H:%M'),'credit':GEO['credit']}
def motion_for(language,audio_duration,labels):
    visual_language=GRAPHIC if GRAPHIC!='auto' else language
    long_report=language=='fr' and FRENCH_LENGTH=='long'
    key=(visual_language,language,long_report,round(audio_duration,3),tuple((round(a,3),round(b,3)) for a,b,_ in labels))
    if key in motions:return motions[key]
    tag=visual_language+'-'+language+('-long' if long_report else '-short')+f'-{audio_duration:.3f}'
    values=dict(name=name if visual_language=='fr' else krname,obs=obs,fresh=fresh,pressure=number('pressure','hPa'),speed=number('speed','km/h'),distance=distance(),direction=direction if visual_language=='fr' else krdir,coord=coord,warning=warn_fr if visual_language=='fr' else krwarning,checked=checked,track=observed_track(D),bearing=S.get('direction') if fresh else None,forecast=FORECAST)
    logo=logo_transparent(ROOT/'studio-logo.png') if LOGO else None
    if LOGO and logo is None:raise ValueError('Requested logo unavailable')
    files=[]
    # A single observation stays a single observation, even if the TV cards rotate.
    count=max(4,len(frame_images),len(values['track']))
    for i in range(count):
        captured,frame,url=frame_images[i%len(frame_images)] if frame_images else (None,None,None)
        # Do not repeat earlier timestamps within one sequence when two or three frames exist.
        if frame_images and i>=len(frame_images):captured,frame,url=frame_images[-1]
        captured_text=captured.strftime('%d %b %Y %H:%M UTC') if captured else ''
        card=render_card(visual_language,values,frame,captured_text,len(frame_images),i,logo)
        file=TMP/f'tv-{tag}-{i:02d}.png';card.save(file);files.append(file)
        if i==count-1 and visual_language=='fr':card.save(OUT/'weather-4k.png')
    # Separate expanded forecast scenes, one frame for each published coordinate.
    # Reuse the latest real satellite frame only as input; forecast scene is a schematic.
    if FORECAST:
        overview=render_card(visual_language,values,None,'',len(frame_images),count,logo,forecast_step=-1,satellite_map=satellite_map(False,0,1+2*len(FORECAST['points'])))
        file=TMP/f'tv-{tag}-forecast-overview.png';overview.save(file);files.append(file)
        for j in range(len(FORECAST['points'])):
            for pulse in range(2):
                card=render_card(visual_language,values,None,'',len(frame_images),count+j*2+pulse,logo,forecast_step=j,forecast_zoom=True,satellite_map=satellite_map(True,1+j*2+pulse,1+2*len(FORECAST['points'])))
                file=TMP/f'tv-{tag}-forecast-{j:03d}-{pulse}.png';card.save(file);files.append(file)
    if visual_language not in posters:
        poster=OUT/f'poster-{visual_language}-4k.png'
        capture,frame,_=frame_images[-1] if frame_images else (None,None,None)
        card=render_card(visual_language,values,frame,capture.strftime('%d %b %Y %H:%M UTC') if capture else '',len(frame_images),count-1,logo,poster=True)
        assert card.size==(2160,3840)
        card.save(poster);posters[visual_language]=poster.name
    concat=TMP/f'tv-{tag}.txt'
    holds=zoom_scene_holds(count,FORECAST['points'] if FORECAST else [],audio_duration,labels)
    assert len(holds)==len(files) and all(h>0 for h in holds)
    # Extra frames protect the final audio sample from concat rounding.
    holds[-1]+=len(holds)/24+0.2
    concat.write_text(''.join("file '"+str(p)+f"'\nduration {hold:.6f}\n" for p,hold in zip(files,holds))+"file '"+str(files[-1])+"'\n")
    motion=TMP/f'tv-{tag}.mp4'
    # TV-style overview-to-close-up cuts preserve exact coordinates; no blended weather frames.
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(concat),'-vf','fps=24,fade=t=in:st=0:d=0.22,format=yuv420p','-c:v','libx264','-preset','ultrafast','-crf','23','-threads','4','-movflags','+faststart',str(motion)],check=True)
    motions[key]=motion
    return motion
print('Timestamped satellite frames:',len(frame_images))
narration=f"Inside Mauritius, veille cyclonique. {name}. Observation : {obs}. "
if fresh:
    if S.get('pressure') is not None:narration+=f"Pression centrale, {S['pressure']} hectopascals. "
    if S.get('speed') is not None:narration+=f"Déplacement à {S['speed']} kilomètres par heure, direction {direction}. "
    narration+=f"À Maurice : {warn_fr}. "
else:narration+="Les conditions actuelles ne sont pas vérifiées. "
narration+=("Image satellite publiée par les services météorologiques. " if sat else "Image satellite indisponible. ")+forecast_words(FORECAST,'fr')+" Suivez les avertissements officiels de la météo de Maurice."
if FRENCH_LENGTH=='long':
    parts=["Bonjour et bienvenue dans le journal météo d'Inside Mauritius.",
           "Voici le point sur la surveillance cyclonique dans le sud-ouest de l'océan Indien."]
    if S.get('name') and S.get('observed'):
        parts.extend([f"Le dernier bulletin récupéré mentionne {name}.",f"L'observation est datée du {obs}."])
    else:parts.append("Les détails d'un système tropical ne sont pas confirmés.")
    if fresh and S.get('name'):
        if S.get('pressure') is not None:parts.append(f"La pression centrale indiquée est de {S['pressure']} hectopascals.")
        if S.get('speed') is not None:parts.append(f"Le déplacement annoncé est de {S['speed']} kilomètres par heure.")
        if S.get('direction'):parts.append(f"La direction signalée est le {direction}.")
        dist=distance()
        if dist!='—':parts.append("La distance estimée par rapport à Maurice est de "+dist.replace(',',' ')+".")
    elif not fresh:parts.append("La situation actuelle n'a pas pu être vérifiée. Les données affichées sont anciennes ou incomplètes.")
    if len(frame_images)>1:parts.append(f"À l'écran, une séquence de {len(frame_images)} images satellite datées, dans leur ordre chronologique.")
    elif sat:parts.append("Une seule image satellite est disponible. Elle ne montre pas l'évolution des nuages.")
    else:parts.append("Les images satellite ne sont pas disponibles pour ce bulletin.")
    points=observed_track(D)
    if len(points)>1:parts.append("La carte présente les positions successives réellement relevées, sans prolongement prévisionnel.")
    elif points:parts.append("La carte indique une seule position relevée. Aucune trajectoire observée ne peut encore être tracée.")
    else:parts.append("Aucune position confirmée ne peut être représentée.")
    parts.append(f"Pour Maurice, au moment de la consultation : {warn_fr}." if fresh else "L'avertissement actuel à Maurice n'a pas été vérifié.")
    parts.append(forecast_words(FORECAST,'fr'))
    parts.append("Pour votre sécurité, consultez les bulletins officiels de la météo de Maurice.")
    parts.append("Merci de suivre Inside Mauritius.")
    narration=" ".join(parts)
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
kreol+=("Zimaz satelit pibliye par servis meteo. " if sat else "Zimaz satelit pa disponib. ")+forecast_words(FORECAST,'mfe')+" Swiv avertisman ofisiel servis meteo Moris."
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
voices={}; videos={}; previews={}; captions={}; formats={}; report_durations={}; duration_adjustments={}; quality_checks={}
def duration(p):
    return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(p)],text=True).strip())
def timecode(s,sep='.'):
    ms=max(0,round(s*1000));h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);sec,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{sec:02}{sep}{ms:03}'
def speak(gender,script,audio,language):
    choice='tom' if gender=='male' else 'siwis'
    model=ROOT/'voice-model'/f'fr_FR-{choice}-medium.onnx'
    if model.exists() and model.with_suffix('.onnx.json').exists():
        try:
            subprocess.run(['python','-m','piper','--model',str(model),'--output_file',str(audio)],input=script,text=True,check=True,timeout=45)
            return 'Piper Tom neural French' if gender=='male' else 'Piper SIWIS neural French'
        except Exception as e:print('Neural voice unavailable:',str(e))
    variant='fr+m3' if gender=='male' else 'fr+f3'
    subprocess.run(['espeak-ng','-v',variant,'-s','140' if language=='mfe' else '150','-w',str(audio),script],check=True)
    return 'eSpeak French fallback ('+gender+')'
def sentence_audio(code,script,gender,language):
    # Each sentence has its own measured audio duration, so captions are not guessed.
    sentences=[x.strip() for x in re.split(r'(?<=[.!?])\s+',script) if x.strip()]
    parts=[]; labels=[]; engines=[]; pos=0.0
    for i,sentence in enumerate(sentences):
        raw=TMP/f'{code}-{i}-raw.wav';part=TMP/f'{code}-{i}.wav'
        engines.append(speak(gender,sentence,raw,language))
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(raw),'-af',f'atempo={SPEED},volume={VOLUME},highpass=f=70,alimiter=limit=0.9','-ar','24000','-ac','1','-c:a','pcm_s16le',str(part)],check=True)
        end=pos+duration(part);labels.append((pos,end,sentence));pos=end;parts.append(part)
    manifest=TMP/f'{code}-audio.txt';manifest.write_text(''.join("file '"+str(p)+"'\n" for p in parts))
    audio=TMP/f'{code}.wav'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(manifest),'-c:a','copy',str(audio)],check=True)
    # Fit the measured narration to approximately one minute, preserving all words.
    if language=='fr' and FRENCH_LENGTH=='long':
        actual=duration(audio)
        if not math.isfinite(actual) or actual<=0:raise ValueError('Invalid speech duration')
        factor=actual/60.0
        if 0.80<=factor<=1.25:
            adjusted=TMP/f'{code}-timed.wav'
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(audio),'-af',f'atempo={factor:.8f}','-c:a','pcm_s16le',str(adjusted)],check=True)
            actual_new=duration(adjusted)
            labels=[(a*actual_new/actual,b*actual_new/actual,s) for a,b,s in labels]
            audio=adjusted
            duration_adjustments[code]=round(factor,4)
        else:
            print(f'{code}: preserving natural duration {actual:.2f}s rather than forcing tempo')
            duration_adjustments[code]=1.0
        print(f'{code}: extended French duration {duration(audio):.2f}s')
    report_durations[code]=round(duration(audio),2)
    vtt=OUT/f'captions-{code}.vtt';srt=TMP/f'captions-{code}.srt'
    vtt.write_text('WEBVTT\n\n'+''.join(f'{timecode(a)} --> {timecode(b)}\n{s}\n\n' for a,b,s in labels),encoding='utf-8')
    srt.write_text(''.join(f'{i+1}\n{timecode(a,",")} --> {timecode(b,",")}\n{s}\n\n' for i,(a,b,s) in enumerate(labels)),encoding='utf-8')
    preview=OUT/f'voice-{code}.mp3'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(audio),'-c:a','libmp3lame','-b:a','96k',str(preview)],check=True)
    portrait_ass=TMP/f'captions-{code}-portrait.ass';landscape_ass=TMP/f'captions-{code}-landscape.ass'
    ass_captions(labels,portrait_ass);ass_captions(labels,landscape_ass,True)
    return audio,srt,preview,vtt,' / '.join(sorted(set(engines))),portrait_ass,landscape_ass,labels
for code,script,gender,language in [('fr',narration,'female','fr'),('fr-male',narration,'male','fr'),('mfe',kreol,'female','mfe'),('mfe-male',kreol,'male','mfe')]:
    audio,srt,preview,vtt,engine,portrait_ass,landscape_ass,labels=sentence_audio(code,script,gender,language)
    voices[code]=engine+(' · Kreol approximation, review pronunciation' if language=='mfe' else '')
    previews[code]=preview.name;captions[code]=vtt.name
    if PREVIEW:continue
    video=OUT/f'weather-{code}.mp4'
    audio_duration=duration(audio)
    if not math.isfinite(audio_duration) or audio_duration<=0:raise ValueError('Invalid narration duration')
    motion=motion_for(language,audio_duration,labels)
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(motion),'-i',str(audio),'-i',str(srt),'-map','0:v:0','-map','1:a:0','-map','2:s:0','-c:v','copy','-c:a','aac','-b:a','160k','-c:s','mov_text','-metadata:s:s:0','language='+('fra' if language=='fr' else 'mfe'),'-disposition:s:0','0','-t',f'{audio_duration:.6f}','-movflags','+faststart',str(video)],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(video)]))
    video_stream=next(x for x in probe['streams'] if x['codec_type']=='video')
    audio_stream=next(x for x in probe['streams'] if x['codec_type']=='audio')
    assert video_stream['width']==2160 and video_stream['height']==3840
    assert any(x.get('codec_type')=='subtitle' for x in probe['streams'])
    assert abs(float(video_stream['duration'])-float(audio_stream['duration']))<0.15,'Video and narration duration mismatch'
    videos[code]=video.name
    # Social-ready versions keep the complete original image and reserve a separate
    # subtitle strip. Landscape has the full satellite image on the left and the
    # original dated bulletin on the right; no extrapolated cloud motion.
    formats[code]={'original':video.name}
    quality_checks[code]={'original':{'width':video_stream['width'],'height':video_stream['height'],'audio':True,'caption_check':True,'av_delta':abs(float(video_stream['duration'])-float(audio_stream['duration'])),'caption_mode':'selectable subtitle stream'}}
    for variant,width,height in [('4k',2160,3840),('hd',1080,1920),('landscape',1920,1080),('landscape4k',3840,2160)]:
        dest=OUT/f'weather-{code}-{variant}.mp4'
        if variant in ('landscape','landscape4k'):
            # Complete satellite panel plus full dated bulletin. Captions occupy a
            # separate bottom band, not the image or website address.
            factor=2 if variant=='landscape4k' else 1
            layout=f"split=2[main][detail];[main]scale={486*factor}:{864*factor}[card];[detail]crop=2016:1740:72:620,scale={1344*factor}:{864*factor}:force_original_aspect_ratio=decrease,pad={1344*factor}:{864*factor}:(ow-iw)/2:(oh-ih)/2:color=0x102337[large];[large][card]hstack=inputs=2,pad={width}:{height}:{45*factor}:{20*factor}:color=0x07121e"
            vf=layout+f",ass={landscape_ass}"
        else:
            vf=f"scale={width}:{height},ass={portrait_ass}"
        filters=['-filter_complex','[0:v]'+vf+'[out]','-map','[out]'] if variant in ('landscape','landscape4k') else ['-vf',vf,'-map','0:v:0']
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(video),*filters,'-map','0:a:0','-c:v','libx264','-preset','ultrafast','-crf','24','-threads','4','-pix_fmt','yuv420p','-c:a','copy','-t',f'{audio_duration:.6f}','-movflags','+faststart',str(dest)],check=True)
        check=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(dest)]))
        vv=next(x for x in check['streams'] if x['codec_type']=='video');av=next(x for x in check['streams'] if x['codec_type']=='audio')
        assert (vv['width'],vv['height'])==(width,height)
        assert abs(float(vv['duration'])-float(av['duration']))<0.20
        formats[code][variant]=dest.name
        quality_checks[code][variant]={'width':vv['width'],'height':vv['height'],'audio':True,'caption_check':portrait_ass.is_file() and landscape_ass.is_file(),'caption_mode':'ASS render completed; visual placement requires review','av_delta':abs(float(vv['duration'])-float(av['duration']))}
        print(f'{code}: {variant} embedded captions, {width}x{height}, verified')
    print(f'{code}: 4K/audio/subtitles verified ({audio_duration:.2f}s); {voices[code]}')
(OUT/'source.json').write_text(json.dumps({'observation':S,'checked_at':D.get('checked_at'),'warning':warning,'source_status':D.get('source_status'),'satellite_url':image_url,'satellite_capture':image_time,'generated_at':now.isoformat(),'video_resolution':'2160x3840','voice':voices,'satellite_frame_count':len(frame_images),'satellite_frame_times':[f[0].isoformat() for f in frame_images],'voice_attribution':'SIWIS French Speech Synthesis Database / Piper SIWIS, CC BY 4.0 (when neural voice used)','videos':videos,'previews':previews,'captions':captions,'voice_speed':SPEED,'voice_volume':VOLUME,'voice_model_sources':{'siwis':'https://huggingface.co/rhasspy/piper-voices/blob/main/fr/fr_FR/siwis/medium/MODEL_CARD','tom':'https://huggingface.co/rhasspy/piper-voices/blob/main/fr/fr_FR/tom/medium/MODEL_CARD'},'preview_only':PREVIEW,'formats':formats,'observation_key':fingerprint(D),'report_key':report_key(D,FORECAST),'official_forecast':FORECAST,'geographic_satellite_overlay':GEO,'forecast_source':'Météo-France RSMC La Réunion via WMO' if FORECAST else None,'forecast_note':'Issued positions only, no interpolated positions or forecast landfall','publication_status':'review_required','french_length':FRENCH_LENGTH,'report_durations':report_durations,'duration_adjustments':duration_adjustments,'studio_version':25,'posters':posters,'poster_resolution':'2160x3840','poster_publication_status':'review_required','quality_checks':quality_checks,'sequence_note':'Chronological sequence fitted to measured narration; no simulated cloud motion','track_points':observed_track(D),'track_note':'Recorded bulletin positions only; satellite times are independent','graphic_language':GRAPHIC,'logo_included':LOGO,'subtitle_layout':'V24 larger type, dedicated safe area, sentence timed'},indent=2,ensure_ascii=False))
print('Videos rendered. Satellite included:',bool(sat))
