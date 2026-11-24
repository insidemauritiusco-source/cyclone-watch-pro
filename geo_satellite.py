"""Georeferenced, timestamped EUMETSAT WMS imagery for dated forecast graphics.
No attempt to infer the projection of MMS JPEGs. No simulated cloud frames.
WMS 1.3.0 EPSG:4326 BBOX is latitude,longitude,latitude,longitude.
"""
import datetime as dt, io, math, re, hashlib, urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from PIL import Image, ImageStat
from forecast_video import timestamp, zoom_bounds, inside
UTC=dt.timezone.utc
BASE='https://view.eumetsat.int/geoserver/wms'
LAYER='msg_iodc:ir108'
COAST='overlay:vector-overlay'
SIZE=(1800,1140)
POLICY='https://www.eumetsat.int/legal-framework/data-policy'
def url(params):
    return BASE+'?'+urllib.parse.urlencode(params)
def request(params,limit):
    req=urllib.request.Request(url(params),headers={'User-Agent':'InsideMauritiusCycloneWatch/1.0','Accept':'*/*'})
    with urllib.request.urlopen(req,timeout=15) as r:
        end=urllib.parse.urlsplit(r.geturl())
        if end.scheme!='https' or end.hostname!='view.eumetsat.int' or r.status!=200:raise ValueError('Unexpected EUMETSAT response')
        data=r.read(limit+1)
    if len(data)>limit:raise ValueError('Response exceeds size limit')
    return data
def tag(el):return el.tag.rsplit('}',1)[-1]
def child(el,name):return next((x for x in el if tag(x)==name),None)
def content(el,name):
    x=child(el,name);return (x.text or '').strip() if x is not None else ''
def capabilities(raw,name):
    root=ET.fromstring(raw)
    if tag(root)!='WMS_Capabilities' or root.attrib.get('version')!='1.3.0':raise ValueError('Unexpected WMS capabilities')
    def walk(el,crs=None,dimension=None,extent=None):
        if tag(el)=='Layer':
            crs=set(crs or [])|{s for x in el if tag(x)=='CRS' for s in (x.text or '').split()}
            for x in el:
                if tag(x)=='Dimension' and x.get('name','').lower()=='time':
                    dimension=(x.text or '').strip()
                if tag(x)=='EX_GeographicBoundingBox':
                    try:extent=tuple(float(content(x,k)) for k in ('westBoundLongitude','eastBoundLongitude','southBoundLatitude','northBoundLatitude'))
                    except ValueError:extent=None
            if content(el,'Name')==name:
                return (crs,dimension,extent)
        for x in el:
            r=walk(x,crs,dimension,extent)
            if r:return r
    result=walk(root)
    if not result or 'EPSG:4326' not in result[0]:raise ValueError('Required WMS layer or CRS not advertised')
    return result
def advertised_times(spec,now):
    """Only explicit times or exact fixed-duration advertised intervals.
    Exclude latest/now aliases and anything less than one hour old.
    """
    if not spec:return []
    oldest=now-dt.timedelta(hours=24);newest=now-dt.timedelta(hours=1)
    times=set()
    for item in spec.split(','):
        fields=item.strip().split('/')
        if len(fields)==1:
            x=timestamp(fields[0].replace('Z','+00:00'))
            if x and oldest<=x<=newest:times.add(x.astimezone(UTC))
        elif len(fields)==3:
            a=timestamp(fields[0].replace('Z','+00:00'));b=timestamp(fields[1].replace('Z','+00:00'))
            m=re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?',fields[2])
            if not a or not b or not m:continue
            step=dt.timedelta(hours=int(m[1] or 0),minutes=int(m[2] or 0),seconds=int(m[3] or 0))
            if step<dt.timedelta(minutes=5):continue
            k=max(0,math.ceil((oldest-a)/step));x=a+k*step
            for _ in range(300):
                if x>min(b,newest):break
                times.add(x.astimezone(UTC));x+=step
    return sorted(times)
def bbox_params(bounds,layer,when=None):
    lo,hi,south,north=bounds
    if not -180<=lo<hi<=180 or not -90<=south<north<=90:raise ValueError('Invalid bbox')
    p=dict(service='WMS',version='1.3.0',request='GetMap',layers=layer,styles='',crs='EPSG:4326',bbox=','.join(format(x,'.12g') for x in (south,lo,north,hi)),width=SIZE[0],height=SIZE[1],format='image/png',transparent='TRUE',exceptions='XML')
    if when:p['time']=when.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    return p
def pixel(bounds,lat,lon):
    lo,hi,south,north=bounds
    return (lon-lo)/(hi-lo)*SIZE[0],(north-lat)/(north-south)*SIZE[1]
def decode(raw,weather=True):
    with Image.open(io.BytesIO(raw)) as src:
        if src.format!='PNG' or src.size!=SIZE:raise ValueError('Unexpected WMS raster')
        im=src.convert('RGBA')
    if weather:
        if im.getchannel('A').histogram()[255]<SIZE[0]*SIZE[1]*.85:raise ValueError('Incomplete satellite coverage')
        if max(ImageStat.Stat(im.convert('RGB')).stddev)<4:raise ValueError('Blank satellite image')
    return im
def covers(bounds,extent):
    if not extent:return False
    lo,hi,south,north=bounds;w,e,s,n=extent
    return w<=lo<hi<=e and s<=south<north<=n
def build(data,forecast,now,fetch=request):
    """Return two consistently projected views or an explicitly labelled fallback.
    Use no more than four real image times and no fabricated intermediate images.
    """
    result={'status':'unavailable','reason':'No verified matching forecast','source':BASE,'layer':LAYER,'crs':'EPSG:4326','policy':POLICY,'frames':[]}
    if not forecast:return result,{}
    from tv_layout import observed_track
    pts=observed_track(data)+[forecast['anchor']]+forecast['points']
    if not all(inside(p) for p in pts):return result,{}
    wide=(min([43]+[p['lon']-2 for p in pts]),max([83]+[p['lon']+2 for p in pts]),min([-29]+[p['lat']-2 for p in pts]),max([-4]+[p['lat']+2 for p in pts]))
    close=zoom_bounds(pts)
    try:
        _,spec,extent=capabilities(fetch(dict(service='WMS',version='1.3.0',request='GetCapabilities',namespace='msg_iodc'),8_000_000),LAYER)
        times=advertised_times(spec,now)
        if not times:raise ValueError('No exact advertised image timestamps at least one hour old')
        if not covers(wide,extent) or not covers(close,extent):raise ValueError('Forecast area outside advertised satellite coverage')
        # Limit the sequence to four times over the last six hours where possible.
        recent=[x for x in times if x>=now-dt.timedelta(hours=6)]
        times=recent or times[-1:]
        n=min(4,len(times));chosen=[times[round(i*(len(times)-1)/(n-1))] for i in range(n)] if n>1 else times[-1:]
        coastline={}
        try:
            capabilities(fetch(dict(service='WMS',version='1.3.0',request='GetCapabilities',namespace='overlay'),8_000_000),COAST)
            for key,bb in [('wide',wide),('close',close)]:
                coastline[key]=decode(fetch(bbox_params(bb,COAST),12_000_000),False)
            if any(x.getchannel('A').getextrema()[0]!=0 or x.getchannel('A').getextrema()[1]==0 for x in coastline.values()):raise ValueError('Invalid coast transparency')
        except Exception as e:
            coastline={};print('Geographic coast layer unavailable:',str(e))
        imgs={};seen=set()
        for when in chosen:
            pair={};hashes={}
            try:
                for key,bb in [('wide',wide),('close',close)]:
                    raw=fetch(bbox_params(bb,LAYER,when),12_000_000);im=decode(raw)
                    for p in pts:
                        x,y=pixel(bb,p['lat'],p['lon'])
                        if not (0<=x<SIZE[0] and 0<=y<SIZE[1]) or im.getpixel((int(x),int(y)))[3]<250:raise ValueError('Missing satellite data at official point')
                    hashes[key]=hashlib.sha256(im.tobytes()).hexdigest()
                    if key in coastline:im=Image.alpha_composite(im,coastline[key])
                    pair[key]=im.convert('RGB')
                if hashes['close'] in seen:continue
                seen.add(hashes['close'])
                stamp=when.isoformat();imgs[stamp]=pair
                result['frames'].append({'captured_at':stamp,'sha256':hashes})
            except Exception as e:print('Geographic satellite frame rejected:',str(e))
        if not imgs:raise ValueError('No usable timestamped raster pairs')
        result.update(status='ok',reason=None,bounds={'wide':wide,'close':close},coastline=COAST if coastline else None,credit='Contains modified EUMETSAT Meteosat data '+str(now.year),timestamp_note='Observed satellite imagery, at least one hour delayed; independent of bulletin validity times; cloud parallax possible')
        return result,imgs
    except Exception as e:
        result.update(status='unavailable',reason=str(e),frames=[])
        return result,{}
