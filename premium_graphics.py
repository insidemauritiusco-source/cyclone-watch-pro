"""Broadcast graphics only: no forecast computation or calibrated temperature claims."""
import io,json,math,urllib.request,urllib.parse,datetime as dt
from PIL import Image,ImageDraw
NE_BASE='https://raw.githubusercontent.com/nvkelso/natural-earth-vector/v5.1.2/geojson/'
NE_FILES=('ne_10m_coastline.geojson','ne_10m_minor_islands_coastline.geojson')
NE_CREDIT='Natural Earth 1:10m (v5.1.2; generalized; not for navigation)'
# Fixed mapping of DISPLAY pixel brightness, not radiometric temperatures.
PALETTE=((0,(8,20,42)),(64,(26,57,98)),(128,(58,132,163)),(192,(139,211,211)),(224,(250,191,76)),(255,(246,80,73)))
def palette_rgb(value):
    value=max(0,min(255,value))
    for (a,c),(b,d) in zip(PALETTE,PALETTE[1:]):
        if value<=b:return tuple(round(x+(y-x)*(value-a)/(b-a)) for x,y in zip(c,d))
    return PALETTE[-1][1]
def enhance(im):
    """Only recolour grayscale source pixels; retain alpha and pixel geometry."""
    rgb=im.convert('RGB')
    from PIL import ImageChops
    r,g,b=rgb.split()
    if max(ImageChops.difference(r,g).getextrema()[1],ImageChops.difference(r,b).getextrema()[1])>2:
        return im.copy(),False
    gray=rgb.convert('L')
    lut=[palette_rgb(i) for i in range(256)]
    result=Image.merge('RGB',tuple(gray.point([p[c] for p in lut]) for c in range(3))).convert('RGBA')
    result.putalpha(im.convert('RGBA').getchannel('A'))
    return result,True
def fetch_ne(name):
    if name not in NE_FILES:raise ValueError('Unexpected coastline file')
    url=NE_BASE+name
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'InsideMauritiusCycloneWatch/1.0'}),timeout=20) as r:
        if r.geturl()!=url or r.status!=200:raise ValueError('Unexpected coastline response')
        raw=r.read(16_000_001)
    if len(raw)>16_000_000:raise ValueError('Coastline exceeds limit')
    return json.loads(raw)
def lines_from_geojson(data):
    if data.get('type')!='FeatureCollection':raise ValueError('Invalid coastline GeoJSON')
    for f in data['features']:
        geo=f.get('geometry') or {}
        coords=geo.get('coordinates',[])
        if geo.get('type')=='LineString':coords=[coords]
        elif geo.get('type')!='MultiLineString':continue
        for line in coords:
            if len(line)<2:continue
            if not all(len(p)>=2 and all(type(q) in (int,float) and math.isfinite(q) for q in p[:2]) and -180<=p[0]<=180 and -90<=p[1]<=90 for p in line):raise ValueError('Invalid coastline coordinate')
            yield line
def clip_segment(a,b,bounds):
    lo,hi,s,n=bounds;x,y=a[:2];u,v=b[:2];dx=u-x;dy=v-y
    if abs(dx)>180:return None
    low,high=0.,1.
    for p,q in ((-dx,x-lo),(dx,hi-x),(-dy,y-s),(dy,n-y)):
        if p==0:
            if q<0:return None
        else:
            k=q/p
            if p<0:low=max(low,k)
            else:high=min(high,k)
            if low>high:return None
    return ((x+low*dx,y+low*dy),(x+high*dx,y+high*dy))
def coast_image(lines,bounds,size):
    lo,hi,s,n=bounds;w,h=size
    im=Image.new('RGBA',size);d=ImageDraw.Draw(im)
    def xy(p):return ((p[0]-lo)/(hi-lo)*(w-1),(n-p[1])/(n-s)*(h-1))
    for line in lines:
        if max(p[0] for p in line)<lo or min(p[0] for p in line)>hi or max(p[1] for p in line)<s or min(p[1] for p in line)>n:continue
        for a,b in zip(line,line[1:]):
            seg=clip_segment(a,b,bounds)
            if seg:
                pts=[xy(p) for p in seg]
                d.line(pts,fill=(5,20,33,255),width=5)
                d.line(pts,fill=(225,243,248,255),width=2)
    return im
def coast_layers(bounds,size,fetch=fetch_ne):
    lines=[line for name in NE_FILES for line in lines_from_geojson(fetch(name))]
    if not lines:raise ValueError('No geographic coastline geometry')
    out={key:coast_image(lines,bb,size) for key,bb in bounds.items()}
    if not out['wide'].getchannel('A').getbbox():raise ValueError('No coastline in regional view')
    return out
def satellite_time_label(stamp):
    x=dt.datetime.fromisoformat(stamp.replace('Z','+00:00'))
    if x.tzinfo is None:raise ValueError('Timestamp has no zone')
    return x.astimezone(dt.timezone.utc).strftime('%d/%m/%Y %H:%M UTC')+' | '+x.astimezone(dt.timezone(dt.timedelta(hours=4))).strftime('%d/%m/%Y %H:%M MUT')
def scale_bar(draw,rect,font,language='fr'):
    x,y,w,h=rect
    for i in range(w):
        draw.line((x+i,y,x+i,y+h),fill=palette_rgb(round(i*255/max(1,w-1))))
    draw.text((x+w+12,y-5),'0–255 · luminosité IR, pas °C' if language=='fr' else '0–255 · limier IR, pa °C',font=font,fill='#e8f4fa')
def fullscreen_frame(image,stamp,credit,enhanced,number,total,bounds=None,forecast=None):
    from PIL import ImageOps,ImageFont
    im=Image.new('RGB',(3840,2160),'#091525');d=ImageDraw.Draw(im)
    font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',n)
    pic=ImageOps.contain(image.convert('RGB'),(3840,1900),Image.Resampling.LANCZOS)
    x0=(3840-pic.width)//2;y0=120+(1900-pic.height)//2
    im.paste(pic,(x0,y0))
    d.text((60,14),'INSIDE MAURITIUS | ANIMATION SATELLITE OBSERVÉE',font=font(49),fill='#42d9ee')
    d.text((60,73),satellite_time_label(stamp)+f'  •  Image {number}/{total}',font=font(36),fill='white')
    if bounds:
        lo,hi,s,n=bounds
        def xy(lat,lon):return (x0+(lon-lo)/(hi-lo)*(pic.width-1),y0+(n-lat)/(n-s)*(pic.height-1))
        def label(x,y,text,color='white',size=35):
            d.text((x,y),text,font=font(size),fill=color,stroke_width=4,stroke_fill='#081525')
        for lon in range(math.ceil(lo/5)*5,math.floor(hi/5)*5+1,5):
            x,_=xy(n,lon);d.line((x,y0,x,y0+pic.height-1),fill='#7995ad',width=2)
            label(x+6,y0+6,f'{lon}°E',size=29)
        for lat in range(math.ceil(s/5)*5,math.floor(n/5)*5+1,5):
            _,y=xy(lat,lo);d.line((x0,y,x0+pic.width-1,y),fill='#7995ad',width=2)
            label(x0+8,y+5,f'{abs(lat)}°S' if lat<0 else f'{lat}°N',size=29)
        for name,lat,lon in [('Madagascar',-19,46.7),('Maurice',-20.2,57.5),('Rodrigues',-19.71,63.42),('Réunion',-21.12,55.53),('Agalega',-10.4,56.6)]:
            if lo<lon<hi and s<lat<n:
                x,y=xy(lat,lon)
                if name!='Madagascar':d.ellipse((x-8,y-8,x+8,y+8),fill='white',outline='#091525',width=3)
                label(x+12,y+12,name,size=36)
        if forecast:
            # Already selected official bulletin; no extrapolation or interpolated positions.
            points=[forecast['anchor']]+forecast['points']
            coords=[xy(p['lat'],p['lon']) for p in points]
            for (x,y),(u,v) in zip(coords,coords[1:]):
                dist=math.hypot(u-x,v-y)
                if not dist:continue
                for k in range(0,math.ceil(dist),28):
                    q=min(k+14,dist)
                    seg=(x+(u-x)*k/dist,y+(v-y)*k/dist,x+(u-x)*q/dist,y+(v-y)*q/dist)
                    d.line(seg,fill='#091525',width=13);d.line(seg,fill='#ffda72',width=7)
            for i,((x,y),p) in enumerate(zip(coords,points)):
                d.ellipse((x-12,y-12,x+12,y+12),fill='#ffda72',outline='#091525',width=4)
                # Alternate labels above/below; close coordinates remain unmodified.
                label(x+18,y+(18 if i%2 else -46),'+'+str(p['hours'])+'h' if i else 'Analyse', '#ffda72',32)
            label(x0+20,y0+54,'PRÉVISIONS DATÉES · MÉTÉO-FRANCE / WMO', '#ffda72',36)
            label(x0+20,y0+100,'Bulletin : '+satellite_time_label(forecast['issued_at'])+' · pas une trajectoire observée', '#ffda72',29)
    if enhanced:
        x,y,width=60,2030,650
        for i in range(width):d.line((x+i,y,x+i,y+32),fill=palette_rgb(round(i*255/(width-1))))
        d.text((x+width+24,y-3),'0–255 · luminosité IR uniquement, pas °C ni intensité cyclonique',font=font(34),fill='#e8f4fa')
    d.text((60,2082),credit+' | Images datées, sans interpolation. Pas une alerte officielle.',font=font(30),fill='#dce8f0')
    return im

def frame_seconds(count):
    if not 2<=count<=15:raise ValueError('Invalid observed frame count')
    return 30/count
