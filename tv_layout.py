"""V14 dated TV weather cards. Real satellite pixels are never extrapolated."""
from PIL import Image, ImageDraw, ImageFont, ImageOps
from collections import deque
from pathlib import Path
import textwrap, re, math
FONT=Path('/usr/share/fonts/truetype/dejavu')
W,H=2160,3840
def font(size,bold=False):
    return ImageFont.truetype(str(FONT/('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf')),size*2)
def logo_transparent(path):
    if not path.is_file():return None
    with Image.open(path) as src:
        img=src.convert('RGBA')
    # Only perimeter-connected near-white pixels are removed, preserving the original asset.
    img.thumbnail((700,400))
    px=img.load(); w,h=img.size; seen=set(); todo=deque()
    def add(x,y):
        if not (0<=x<w and 0<=y<h) or (x,y) in seen:return
        seen.add((x,y));r,g,b,a=px[x,y]
        if a==0 or (min(r,g,b)>232 and max(r,g,b)-min(r,g,b)<20):todo.append((x,y))
    for x in range(w):add(x,0);add(x,h-1)
    for y in range(h):add(0,y);add(w-1,y)
    while todo:
        x,y=todo.popleft();r,g,b,a=px[x,y];px[x,y]=(r,g,b,0)
        for xx,yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):add(xx,yy)
    return ImageOps.contain(img,(250,124),Image.Resampling.LANCZOS)
TEXT={
'fr':dict(title='VEILLE CYCLONIQUE',verified='SOURCE MMS CONSULTÉE',saved='DONNÉES NON VÉRIFIÉES',obs='Observation',sat='SATELLITE MMS / METEOSAT',missing='IMAGE SATELLITE INDISPONIBLE',sequence='Séquence observée · aucune interpolation',single='Image unique · pas de mouvement observé',pressure='PRESSION CENTRALE',speed='DÉPLACEMENT',distance='DISTANCE DE MAURICE',direction='DIRECTION',coords='Coordonnées observées',warning='AVERTISSEMENT À MAURICE',checked='Source vérifiée',ticker1='Suivi indépendant · Consultez les bulletins officiels MMS',ticker2='Heure satellite et heure du bulletin peuvent différer',ticker3='Ni prévision ni alerte officielle · Images datées',credit='Source : Mauritius Meteorological Services (MMS)',subtitle='SOUS-TITRES',unknown='Non signalé'),
'mfe':dict(title='SIVEYANS SIKLON',verified='SOURS MMS KONSILTE',saved='DONE PA VERIFIE',obs='Observasion',sat='SATELIT MMS / METEOSAT',missing='ZIMAZ SATELIT PA DISPONIB',sequence='Sekans observe · pena interpolasion',single='Enn sel zimaz · pa montre mouvman',pressure='PRESION SANTRAL',speed='DEPLASMAN',distance='DISTANS AR MORIS',direction='DIREKSION',coords='Koordoné observe',warning='AVERTISMAN MORIS',checked='Sours verifie',ticker1='Swivi indepandan · Konsilte bilten ofisiel MMS',ticker2='Ler satelit ek ler bilten kapav diferan',ticker3='Pa enn previzion ni alert ofisiel · Zimaz date',credit='Sours : Mauritius Meteorological Services (MMS)',subtitle='SOU TIT',unknown='Pa signale')}
import datetime as _dt
def observed_track(data):
    storm=data.get('storm') or {};name=storm.get('name','')
    if not name:return []
    def system_id(s):
        m=re.search(r'\(([A-Za-z0-9-]+)\)\s*$',s or '')
        return m.group(1).upper() if m else (s or '').casefold()
    ident=system_id(name); points={}
    for p in [*(data.get('history') or []),storm]:
        if not isinstance(p,dict) or system_id(p.get('name',''))!=ident:continue
        try:
            lat,lon=float(p['lat']),float(p['lon'])
            if not (-90<=lat<=90 and -180<=lon<=180):continue
            text=str(p['observed'])
            when=None
            for fmt in ('%d %B %Y %I %p','%d %B %Y %I:%M %p','%d %B %Y %H:%M'):
                try:when=_dt.datetime.strptime(text,fmt);break
                except ValueError:pass
            if when is None:continue
            points[when]={'lat':lat,'lon':lon,'observed':text,'direction':p.get('direction')}
        except (KeyError,ValueError,TypeError):continue
    return [points[x] for x in sorted(points)]

def render_card(language, data, frame, captured, frame_count, phase, logo=None, poster=False):
    t=TEXT[language]; im=Image.new('RGB',(W,H),'#091525');d=ImageDraw.Draw(im)
    def box(x,y,w,h,color,r=0):
        b=(x*2,y*2,(x+w)*2,(y+h)*2)
        if r:d.rounded_rectangle(b,radius=r*2,fill=color)
        else:d.rectangle(b,fill=color)
    def line(x,y,s,size=25,color='#eaf5fa',bold=False,maxw=980):
        s=str(s);f=font(size,bold)
        while size>12 and d.textlength(s,font=f)>maxw*2:
            size-=1;f=font(size,bold)
        d.text((x*2,y*2),s,font=f,fill=color)
    # Keep branded header independent of logo option. Light header is continuous,
    # not an artificial white rectangle behind the optional transparent logo.
    box(0,0,1080,10,'#42d9ee')
    if logo:
        box(0,10,1080,98,'#d9e9f0')
        im.paste(logo,(1940-logo.width//2,115-logo.height//2),logo)
        line(44,24,'INSIDE MAURITIUS',31,'#102638',True,maxw=800)
        line(44,66,'mr.insidemauritius.com/cyclone/',23,'#21536a',True,maxw=820)
    else:
        line(44,24,'INSIDE MAURITIUS',31,bold=True)
        line(44,66,'mr.insidemauritius.com/cyclone/',23,'#83dcec',True)
    box(36,114,1008,70,'#bc343b',8)
    line(55,123,t['title'],45,'white',True)
    line(44,196,data['name'],40,bold=True)
    line(44,248,t['obs']+' : '+data['obs'],24,'#b9d6e0')
    line(44,283,t['verified'] if data['fresh'] else t['saved'],21,'#42d9ee' if data['fresh'] else '#ffc36b',True)
    # Large satellite panel; full original field of view and printed timestamps retained.
    box(36,318,1008,808,'#102337',8)
    line(54,330,t['sat'],23,'#c4deea',True)
    # Satellite imagery and coordinate history are separate: the satellite source
    # need not have the same observation time as the bulletin track.
    points=data.get('track',[]); count=len(points)
    if frame is not None:
        pic=ImageOps.contain(frame,(1984,890),Image.Resampling.LANCZOS)
        im.paste(pic,((W-pic.width)//2,720+(890-pic.height)//2))
        line(54,812,captured,19,'#e0f3f9',True)
        line(54,838,('Dernière image disponible' if language=='fr' else 'Dernie zimaz disponib') if poster else (t['sequence'] if frame_count>1 else t['single']),15,'#aac6d7',maxw=790)
        line(890,838,f'{min(phase+1,frame_count)}/{frame_count}',15,'#42d9ee',True,maxw=115)
        line(730,330,'MMS / METEOSAT',15,'#42d9ee',True,maxw=280)
        box(54,858,970,3,'#28485c')
        box(54,858,max(1,970*min(phase+1,frame_count)/max(1,frame_count)),3,'#42d9ee')
    else:
        line(66,550,t['missing'],28,'#ffc36b',True)
        line(66,602,t['coords']+' : '+data['coord'],22,'#b9d6e0')
    # Regional track schematic: plotted points only; no forecast cone or synthetic center.
    box(48,867,984,244,'#091d2d',7)
    label='TRAJECTOIRE OBSERVÉE · CARTE SCHÉMATIQUE' if language=='fr' else 'TRAJEKTWAR OBSERVE · KART SKEMATIK'
    line(62,875,label,18,'#b9d6e0',True,maxw=940)
    lo=min([43]+[p['lon']-2 for p in points]);hi=max([83]+[p['lon']+2 for p in points])
    south=min([-29]+[p['lat']-2 for p in points]);north=max([-4]+[p['lat']+2 for p in points])
    def xy(lat,lon):return ((86+(lon-lo)/(hi-lo)*900)*2,(906+(north-lat)/(north-south)*146)*2)
    for lon in range(45,81,5):
        x,y=xy(north,lon);d.line((x,y,x,xy(south,lon)[1]),fill='#294558',width=2)
    for lat in range(-5,-26,-5):
        x,y=xy(lat,lo);d.line((x,y,xy(lat,hi)[0],y),fill='#294558',width=2)
    for place,lat,lon in [('Madagascar',-19.4,46.7),('Maurice' if language=='fr' else 'Moris',-20.2,57.5),('Rodrigues',-19.71,63.42),('Agalega',-10.4,56.6),('Réunion',-21.13,55.53)]:
        x,y=xy(lat,lon);d.ellipse((x-5,y-5,x+5,y+5),fill='#bbd4de')
        d.text((x+8,y+7),place,font=font(13),fill='#bbd4de')
    shown=min(count,1+phase) if count else 0
    coords=[xy(p['lat'],p['lon']) for p in points[:shown]]
    if len(coords)>1:d.line(coords,fill='#42d9ee',width=5)
    for i,(x,y) in enumerate(coords):
        r=11 if i==len(coords)-1 else 7
        d.ellipse((x-r,y-r,x+r,y+r),fill='#42d9ee',outline='white',width=2)
        d.text((x+15,y-22),str(i+1),font=font(13,True),fill='white')
    # A compass arrow reports the latest bulletin direction only, never a predicted path.
    direction=str(data.get('bearing') or '').lower().replace('-','').replace(' ','')
    bearings={'north':0,'northnortheast':22.5,'northeast':45,'eastnortheast':67.5,'east':90,'eastsoutheast':112.5,'southeast':135,'southsoutheast':157.5,'south':180,'southsouthwest':202.5,'southwest':225,'westsouthwest':247.5,'west':270,'westnorthwest':292.5,'northwest':315,'northnorthwest':337.5}
    if direction in bearings:
        bx,by=1950,1835; ang=math.radians(bearings[direction]);ex,ey=bx+34*math.sin(ang),by-34*math.cos(ang)
        d.ellipse((bx-42,by-42,bx+42,by+42),fill='#18394c',outline='#b9d6e0',width=2)
        d.text((bx-8,by-40),'N',font=font(9,True),fill='white')
        d.line((bx,by,ex,ey),fill='#ffc36b',width=5)
        d.polygon([(ex,ey),(ex-14*math.sin(ang-.5),ey+14*math.cos(ang-.5)),(ex-14*math.sin(ang+.5),ey+14*math.cos(ang+.5))],fill='#ffc36b')
    if count:
        p=points[shown-1]
        msg=f'{shown}/{count} · '+p['observed']
        if count==1:msg+=(' · point unique, pas de trajectoire' if language=='fr' else ' · enn sel pwin, pena trajektwar')
    else:msg='Aucun point confirmé' if language=='fr' else 'Pena pwin konfirme'
    line(62,1075,msg,17,'#b9d6e0',True,maxw=940)
    # Animate emphasis only, never the measured values.
    stats=[(t['pressure'],data['pressure']),(t['speed'],data['speed']),(t['distance'],data['distance']),(t['direction'],data['direction'])]
    for i,(label,val) in enumerate(stats):
        x=36+(i%2)*510;y=1139+(i//2)*91
        box(x,y,498,82,'#1a3c53' if phase%4==i else '#142b41',7)
        box(x,y,5,82,'#42d9ee' if phase%4==i else '#365a70',2)
        line(x+15,y+8,label,18,'#b9d6e0',True,maxw=466)
        line(x+15,y+33,val,30,'#42d9ee',True,maxw=466)
    line(44,1327,t['coords']+' : '+data['coord'],23,'#b9d6e0',True)
    box(36,1361,1008,76,'#392e25',7)
    line(52,1369,t['warning'],17,'#ffc36b',True)
    line(52,1394,data['warning'],28,'#ffc36b',True)
    # Real subtitles are overlaid into this dedicated area at render time.
    box(36,1450,908,166,'#0d2032',9)
    if poster:
        line(54,1465,'BULLETIN DATÉ' if language=='fr' else 'BILTEN DATE',21,'#42d9ee',True)
        line(54,1507,t['ticker1'],22,'#eaf5fa',True,maxw=870)
        line(54,1551,t['ticker3'],19,'#b9d6e0',maxw=870)
    else:line(54,1459,t['subtitle'],15,'#7796aa',True)
    line(44,1632,t['checked']+' : '+data['checked'],22,'#c3d8e6',True)
    line(44,1664,t['credit'],19,'#aac6d7')
    box(36,1702,1008,70,'#16445b',7)
    line(53,1719,t['ticker'+str(phase%3+1)],23,'white',True,maxw=970)
    # Constant safety footer; the rotating news ticker never replaces this warning.
    line(44,1790,t['ticker1'],21,'#b9d6e0',True)
    line(44,1822,t['ticker3'],20,'#b9d6e0')
    line(44,1864,'mr.insidemauritius.com/cyclone/',24,'#42d9ee',True)
    return im
def ass_captions(labels,path,landscape=False):
    # ASS coordinates are explicit, independent of the encoded pixel dimensions.
    width,height=(1920,1080) if landscape else (1080,1920)
    x,y=(960,908) if landscape else (480,1485)
    size=34 if landscape else 32
    margin=110 if landscape else 88
    header=f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,DejaVu Sans,{size},&H00FFFFFF,&H00FFFFFF,&H00101A29,&H80000000,-1,0,0,0,100,100,0,0,1,1,0,8,{margin},{margin},0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def tc(s):
        n=round(max(0,s)*100);hh,n=divmod(n,360000);mm,n=divmod(n,6000);ss,cs=divmod(n,100)
        return f'{hh}:{mm:02}:{ss:02}.{cs:02}'
    rows=[]
    for start,end,s in labels:
        # Fit all words, including longer safety phrases. Do not truncate.
        s=s.replace('\\','/').replace('{','(').replace('}',')')
        maxpx=1650 if landscape else 820
        f=font(size,True); pieces=[]; row=''
        for word in s.split():
            test=(row+' '+word).strip()
            if row and f.getlength(test)>maxpx*2:pieces.append(row);row=word
            else:row=test
        if row:pieces.append(row)
        while len(pieces)>3 and size>18:
            size-=1;f=font(size,True);pieces=[];row=''
            for word in s.split():
                test=(row+' '+word).strip()
                if row and f.getlength(test)>maxpx*2:pieces.append(row);row=word
                else:row=test
            if row:pieces.append(row)
        rows.append(f'Dialogue: 0,{tc(start)},{tc(end)},Default,,0,0,0,,'+r'{\an8\pos('+str(x)+','+str(y)+r')\fs'+str(size)+'}'+r'\N'.join(pieces))
    path.write_text(header+'\n'.join(rows)+'\n',encoding='utf-8')
