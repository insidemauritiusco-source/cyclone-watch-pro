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
sat=None; image_time=None; image_url=None
try:
    m=json.loads((ROOT/'media.json').read_text())
    url=m['satellite']['url']; p=urllib.parse.urlparse(url)
    if p.scheme!='https' or p.hostname!='metservice.intnet.mu' or not p.path.startswith('/mmsimages/'): raise ValueError('Unapproved image source')
    capture=dt.datetime.fromisoformat(m['satellite']['captured_at'])
    if capture.tzinfo is None:raise ValueError('Capture time lacks timezone')
    if not -600 <= (now-capture).total_seconds() <= 24*3600: raise ValueError('Image is not recent')
    req=urllib.request.Request(url,headers={'User-Agent':'InsideMauritiusCycloneWatch/1.0','Referer':'https://metservice.intnet.mu/satellite-imagery.php','Accept':'image/*'})
    with urllib.request.urlopen(req,timeout=25) as response:
        end=urllib.parse.urlparse(response.geturl())
        if end.scheme!='https' or end.hostname!='metservice.intnet.mu' or not end.path.startswith('/mmsimages/'):raise ValueError('Unexpected source redirect')
        raw=response.read(15_000_001)
    if len(raw)>15_000_000:raise ValueError('Image too large')
    import io
    with Image.open(io.BytesIO(raw)) as src: sat=ImageOps.contain(src.convert('RGB'),(1900,1110),Image.Resampling.LANCZOS)
    image_time=capture.strftime('%d %b %Y %H:%M UTC');image_url=url
except Exception as e: print('Satellite unavailable:',str(e))
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
(OUT/'narration-mfe.txt').write_text(kreol)
for code,script in [('fr',narration),('mfe',kreol)]:
    audio=OUT/f'voice-{code}.wav'
    subprocess.run(['espeak-ng','-v','fr','-s','145' if code=='mfe' else '155','-w',str(audio),script],check=True)
    video=OUT/f'weather-{code}.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-framerate','24','-i',str(poster),'-i',str(audio),'-vf','fade=t=in:st=0:d=0.45,format=yuv420p','-c:v','libx264','-preset','ultrafast','-crf','22','-threads','4','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(video)],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(video)]))
    assert any(x.get('codec_type')=='video' and x.get('width')==2160 and x.get('height')==3840 for x in probe['streams'])
    assert any(x.get('codec_type')=='audio' for x in probe['streams'])
(OUT/'source.json').write_text(json.dumps({'observation':S,'checked_at':D.get('checked_at'),'warning':warning,'source_status':D.get('source_status'),'satellite_url':image_url,'satellite_capture':image_time,'generated_at':now.isoformat(),'video_resolution':'2160x3840','voice':{'fr':'French synthetic speech','mfe':'Kreol Morisien text using French speech approximation'},'videos':{'fr':'weather-fr.mp4','mfe':'weather-mfe.mp4'}},indent=2,ensure_ascii=False))
print('Videos rendered. Satellite included:',bool(sat))
