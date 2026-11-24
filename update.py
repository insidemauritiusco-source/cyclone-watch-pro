"""Retrieve MMS public pages. Fail closed if source structure changes."""
import json, re, urllib.request, datetime, pathlib, sys, time
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parent
BASE='https://metservice.intnet.mu/'
class Page(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.skip+=1
        if tag in ('h1','h2','h3','h4','p','td','th','tr','div','br','li'): self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
        if tag in ('h1','h2','h3','h4','p','td','th','tr','div','li'): self.parts.append('\n')
    def handle_data(self, data):
        if not self.skip: self.parts.append(data)
    def text(self): return '\n'.join(' '.join(s.split()) for s in ''.join(self.parts).splitlines() if s.strip())
def section(html, heading):
    p=Page(); p.feed(html); lines=p.text().splitlines()
    # The actual heading follows the global navigation. Use the last
    # heading before the sidebar's Weather heading, not sidebar links.
    for i,line in enumerate(lines):
        if line.casefold()!=heading.casefold(): continue
        for j in range(i+1,len(lines)):
            if lines[j]=='Weather':
                block=lines[i+1:j]
                if block and block[0]!='Cyclone Warning Bulletin Mauritius':
                    return '\n'.join(block)
                break
    raise ValueError('Official bulletin body unavailable')
def get(path):
    req=urllib.request.Request(BASE+path,headers={'User-Agent':'InsideMauritiusCycloneWatch/1.0 (public weather monitor)'})
    with urllib.request.urlopen(req, timeout=25) as res:
        return res.read(2_000_000).decode(res.headers.get_content_charset() or 'utf-8',errors='replace')
def warning(html):
    text=section(html,'Current Cyclone')
    if re.search(r'\bno cyclone warning is in force in Mauritius\b',text,re.I): return 'No warning reported'
    m=re.search(r'cyclone warning\s+(?:of\s+)?class\s+(IV|III|II|I)\b.{0,90}\b(?:in force|issued|maintained)\b', ' '.join(text.split()),re.I)
    return 'Class '+m.group(1).upper() if m else 'Unknown — consult bulletin'
def storm(html):
    t=section(html,'Current Storm/Cyclone'); lines=t.splitlines()
    if re.search(r'\bno (?:active )?(?:storm|cyclone|tropical system)\b',t,re.I): return None
    m=re.search(r'(?i)(\d+(?:\.\d+)?)\s*°?\s*([NS])\s*[,;/ ]*\s*(\d+(?:\.\d+)?)\s*°?\s*([EW])',t)
    if not m: raise ValueError('Position not recognized')
    lat=float(m.group(1))*(-1 if m.group(2).upper()=='S' else 1); lon=float(m.group(3))*(-1 if m.group(4).upper()=='W' else 1)
    if not (-90<=lat<=90 and -180<=lon<=180): raise ValueError('Invalid coordinates')
    name=next((line.strip() for line in lines if re.fullmatch(r'(?:Tropical Disturbance|Tropical Depression|Subtropical Depression|(?:Moderate|Severe) Tropical Storm|(?:(?:Very )?Intense )?Tropical Cyclone)(?:\s+[\w\-]+){0,4}',line.strip(),re.I)),None)
    if not name: raise ValueError('Storm name not recognized')
    def match(pattern):
        x=re.search(pattern,t,re.I); return x.group(1).strip() if x else None
    pressure=match(r'Estimated Central Pressure\s*(\d{3,4})\s*hPa'); speed=match(r'Movement\s*[^\n]*?(\d+(?:\.\d+)?)\s*km/h'); direction=match(r'Movement\s*([^\n\d]+)\s*\d+(?:\.\d+)?\s*km/h'); observed=match(r'Date and Time\s*([^\n]+)')
    if not observed: raise ValueError('Observation time missing')
    return dict(name=name,observed=observed,lat=lat,lon=lon,pressure=int(pressure) if pressure else None,speed=float(speed) if speed else None,direction=direction,wind=None)
def update():
    target=ROOT/'data.json'; old=json.loads(target.read_text()) if target.exists() else {}; checked=datetime.datetime.now(datetime.timezone.utc).isoformat(); errors=[]
    try: w=warning(get('tropical-cyclone/current-cyclone.php'))
    except Exception as e: w='Unknown — source unavailable'; errors.append(str(e))
    if w.startswith('Unknown'): errors.append('Warning not verified')
    try: s=storm(get('current-cyclone.php'))
    except Exception as e: s=old.get('storm'); errors.append(str(e))
    if s and s.get('name')=='Cyclone Warning Bulletin Mauritius': s=None
    history=[x for x in old.get('history',[]) if x.get('name')!='Cyclone Warning Bulletin Mauritius']
    if not errors and s and (not history or history[-1]!=s): history.append(s)
    result=dict(checked_at=checked,source_status='incomplete' if errors else 'ok',warning=w,storm=s,history=history[-100:],errors=errors)
    temp=target.with_suffix('.tmp'); temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)); temp.replace(target); print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
    if '--loop' in sys.argv:
        while True: update(); time.sleep(300)
    else: update()
