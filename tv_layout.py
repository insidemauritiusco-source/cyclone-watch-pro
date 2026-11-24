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
def render_card(language, data, frame, captured, frame_count, phase, logo=None):
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
    if frame is not None:
        pic=ImageOps.contain(frame,(1984,1400),Image.Resampling.LANCZOS)
        im.paste(pic,((W-pic.width)//2,720+(1400-pic.height)//2))
        line(54,1067,captured,23,'#e0f3f9',True)
        line(54,1098,t['sequence'] if frame_count>1 else t['single'],17,'#aac6d7')
    else:
        line(66,650,t['missing'],32,'#ffc36b',True)
        line(66,710,t['coords']+' : '+data['coord'],25,'#b9d6e0')
        line(54,1098,t['ticker3'],17,'#aac6d7')
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
    line(54,1459,t['subtitle'],15,'#7796aa',True)
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
