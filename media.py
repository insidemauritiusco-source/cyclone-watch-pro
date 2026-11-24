"""Optional independent MMS imagery metadata discovery. Never changes cyclone data."""
import datetime, json, urllib.request, urllib.parse, pathlib
from html.parser import HTMLParser
BASE='https://metservice.intnet.mu/'
class Images(HTMLParser):
    def __init__(self):
        super().__init__(); self.candidates=[]
    def handle_starttag(self,tag,attrs):
        if tag!='img': return
        a=dict(attrs); src=a.get('src',''); alt=a.get('alt','')
        url=urllib.parse.urljoin(BASE,src)
        p=urllib.parse.urlparse(url)
        if p.netloc!='metservice.intnet.mu' or not p.path.startswith('/mmsimages/'): return
        if 'satellite' in alt.lower() or 'meteosat' in urllib.parse.unquote(p.path).lower():
            self.candidates.append(url)
result={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'satellite':None}
try:
    req=urllib.request.Request(BASE+'satellite-imagery.php',headers={'User-Agent':'InsideMauritiusCycloneWatch/1.0'})
    with urllib.request.urlopen(req,timeout=15) as r:
        p=Images();p.feed(r.read(2000000).decode(r.headers.get_content_charset() or 'utf-8',errors='replace'))
    if p.candidates:
        result['satellite']={'url':p.candidates[0]}
except Exception as e:
    result['error']=str(e)
pathlib.Path('media.json').write_text(json.dumps(result,indent=2))
