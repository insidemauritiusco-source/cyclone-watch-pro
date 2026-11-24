"""Discover timestamped official MMS satellite image."""
import datetime, json, urllib.request, urllib.parse, pathlib, re
from html.parser import HTMLParser
BASE='https://metservice.intnet.mu/'
UTC=datetime.timezone.utc
def normalize(raw):
    p=urllib.parse.urlsplit(urllib.parse.urljoin(BASE,raw.strip()))
    if p.hostname!='metservice.intnet.mu' or p.username or p.password or p.port not in (None,80,443):return None
    path=urllib.parse.unquote(p.path)
    if not path.startswith('/mmsimages/') or '..' in path.split('/') or not re.search(r'\.(?:jpe?g|png|webp)$',path,re.I):return None
    return urllib.parse.urlunsplit(('https','metservice.intnet.mu',urllib.parse.quote(path,safe='/'),p.query,''))
def capture(url):
    name=urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit('/',1)[-1])
    m=re.search(r'Meteosat(?:[- ]?\d+)?\s+(\d{4}-\d{2}-\d{2})\s+(\d{4})(?:\D|$)',name,re.I)
    if not m:return None
    try:return datetime.datetime.strptime(m.group(1)+' '+m.group(2),'%Y-%m-%d %H%M').replace(tzinfo=UTC)
    except ValueError:return None
class Images(HTMLParser):
    def __init__(self):super().__init__();self.candidates={}
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        for key in (('src','data-src') if tag=='img' else ('href',) if tag=='a' else ()):
            try:url=normalize(a.get(key,'') or '')
            except ValueError:continue
            if url:
                t=capture(url)
                if t:self.candidates[url]=t
now=datetime.datetime.now(UTC)
result={'checked_at':now.isoformat(),'satellite':None,'frames':[],'source_page':BASE+'satellite-imagery.php'}
candidates={}; errors=[]
for page in ('satellite-imagery.php','satellite-images.php','satellite-anim.php'):
    try:
        req=urllib.request.Request(BASE+page,headers={'User-Agent':'InsideMauritiusCycloneWatch/1.0','Accept':'text/html'})
        with urllib.request.urlopen(req,timeout=12) as r:
            if urllib.parse.urlsplit(r.geturl()).hostname!='metservice.intnet.mu':raise ValueError('Unexpected source redirect')
            html=r.read(2000000).decode(r.headers.get_content_charset() or 'utf-8',errors='replace')
        p=Images();p.feed(html);candidates.update(p.candidates)
        for raw in re.findall(r"""['"]([^'"\r\n]*mmsimages/[^'"\r\n]+\.(?:jpg|jpeg|png|webp))['"]""",html,re.I):
            try:
                url=normalize(raw); t=capture(url) if url else None
                if t:candidates[url]=t
            except ValueError:pass
        print('Satellite discovery',page,len(p.candidates))
    except Exception as e:errors.append(page+': '+str(e))
def product(u):
    name=urllib.parse.unquote(urllib.parse.urlsplit(u).path.rsplit('/',1)[-1])
    name=re.sub(r'^20\d{2}-\d{2}-\d{2}_[^_]+_', '',name)
    return re.sub(r'\s+20\d{2}-\d{2}-\d{2}\s+\d{4}.*$', '',name).strip().lower()
eligible=[(u,t) for u,t in candidates.items() if -600<=(now-t).total_seconds()<=86400]
if eligible:
    # Prefer the latest product; preserve its exact timestamped sequence.
    u,t=max(eligible,key=lambda x:x[1])
    result['satellite']={'url':u,'captured_at':t.isoformat()}
    matching={time:url for url,time in eligible if product(url)==product(u)}
    result['frames']=[{'url':url,'captured_at':time.isoformat()} for time,url in sorted(matching.items())[-24:]]
else:result['error']='No recent timestamped official satellite image found'
if errors:result['discovery_errors']=errors
pathlib.Path('media.json').write_text(json.dumps(result,indent=2))
print('Satellite metadata:',json.dumps(result))
