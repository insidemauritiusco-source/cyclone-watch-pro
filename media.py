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
result={'checked_at':now.isoformat(),'satellite':None,'source_page':BASE+'satellite-imagery.php'}
try:
    req=urllib.request.Request(result['source_page'],headers={'User-Agent':'InsideMauritiusCycloneWatch/1.0'})
    with urllib.request.urlopen(req,timeout=20) as r:
        p=Images();p.feed(r.read(2000000).decode(r.headers.get_content_charset() or 'utf-8',errors='replace'))
    eligible=[(url,t) for url,t in p.candidates.items() if -600 <= (now-t).total_seconds() <= 86400]
    if eligible:
        url,t=max(eligible,key=lambda x:x[1]);result['satellite']={'url':url,'captured_at':t.isoformat()}
    else:result['error']='No recent timestamped official satellite image found'
except Exception as e:result['error']=str(e)
pathlib.Path('media.json').write_text(json.dumps(result,indent=2))
print('Satellite metadata:',json.dumps(result))
