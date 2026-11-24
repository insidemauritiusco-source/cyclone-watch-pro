"""Read only issuer-identified Météo-France marine cyclone bulletins from WMO."""
import datetime as dt, json, re, urllib.request, pathlib
from html.parser import HTMLParser
UTC=dt.timezone.utc
URL='https://wwmiws.wmo.int/index.php/metareas/bulletinset/8S/html'
class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
        if tag in ('br','p','div','pre','tr','li'):self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
        if tag in ('p','div','pre','tr','li'):self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
def iso(d):return d.isoformat()
def parse(text,now):
    text=re.sub(r'\s+',' ',text.upper())
    results=[]
    for section in re.split(r'(?=\b[A-Z]{4}\d{2}\s+[A-Z]{4}\s+\d{6}\b)',text):
        if not re.match(r'WTIO2[0-9]\s+FMEE\s+\d{6}\b',section):continue
        issued=re.search(r'ISSUED BY METEO[- ]FRANCE\s*/\s*TROPICAL CYCLONE CENTER\s*/\s*LA REUNION\s+(\d{2}/\d{2}/\d{4})\s+AT\s+(\d{4})\s+UTC',section)
        num=re.search(r'WARNING NUMBER:\s*(\d+)\s*/\s*(\d+)',section)
        if not issued or not num:continue
        try:stamp=dt.datetime.strptime(issued[1]+' '+issued[2],'%d/%m/%Y %H%M').replace(tzinfo=UTC)
        except ValueError:continue
        if not dt.timedelta(minutes=-5)<=now-stamp<=dt.timedelta(hours=24):continue
        if not 1<=int(num[2])<=99:continue
        split=section.split('FORECAST POSITION AND INTENSITY:',1)
        if len(split)!=2:continue
        anchor=re.search(r'POSITION:\s*WITHIN\s+\d+\s+NM\s+RADIUS OF POINT\s+(\d{1,2}(?:\.\d+)?)\s*S\s*/\s*(\d{1,3}(?:\.\d+)?)\s*E',split[0])
        if not anchor:continue
        lat,lon=-float(anchor[1]),float(anchor[2])
        if not -45<=lat<0 or not 30<=lon<=90:continue
        # Require the observation reference time to equal the bulletin issue time
        # because the published forecast lead times are relative to that reference.
        begin=re.search(r'BEGINNING OF VALIDITY:[^:]*?(\d{2}/\d{2}/\d{4})\s+AT\s+(\d{4})\s+UTC',split[0])
        if not begin or begin[1]!=issued[1] or begin[2]!=issued[2]:continue
        block=split[1].split('OTHER INFORMATION:',1)[0]
        pattern=r'\b(\d{1,3})H,\s*VALID\s+(\d{4}/\d{2}/\d{2})\s+AT\s+(\d{2})(?:00)?\s+UTC:\s*(\d{1,2}(?:\.\d+)?)\s*S\s*/\s*(\d{1,3}(?:\.\d+)?)\s*E\b'
        pts=[]
        for m in re.finditer(pattern,block):
            try:valid=dt.datetime.strptime(m[2]+' '+m[3],'%Y/%m/%d %H').replace(tzinfo=UTC)
            except ValueError:continue
            lead=int(m[1]); y,x=-float(m[4]),float(m[5])
            if not 0<lead<=120 or valid!=stamp+dt.timedelta(hours=lead) or not -45<=y<0 or not 30<=x<=90:continue
            # Read intensity only immediately after this point's published coordinates.
            # The WMO bulletin defines wind as a ten-minute average in knots.
            intensity=re.match(r'\s*,\s*MAX\s+WIND\s*=\s*(\d{1,3})\s*KT\b(?:\s*,\s*(VERY INTENSE TROPICAL CYCLONE|INTENSE TROPICAL CYCLONE|TROPICAL CYCLONE|SEVERE TROPICAL STORM|MODERATE TROPICAL STORM|TROPICAL DEPRESSION|TROPICAL DISTURBANCE|POST-TROPICAL DEPRESSION|REMNANT LOW|EXTRATROPICAL DEPRESSION)\b)?',block[m.end():])
            point=dict(hours=lead,valid_at=iso(valid),lat=y,lon=x)
            if intensity and 0<=int(intensity[1])<=200:
                point['max_wind_kt']=int(intensity[1])
                if intensity[2]:point['classification']=intensity[2]
            pts.append(point)
        if not pts or len({p['hours'] for p in pts})!=len(pts):continue
        pts.sort(key=lambda p:p['hours'])
        if not any(dt.datetime.fromisoformat(p['valid_at'])>now for p in pts):continue
        results.append(dict(system_number=int(num[2]),bulletin_number=int(num[1]),issued_at=iso(stamp),anchor=dict(lat=lat,lon=lon),points=pts))
    return sorted(results,key=lambda x:(x['issued_at'],x['bulletin_number']),reverse=True)
def main():
    now=dt.datetime.now(UTC)
    out=dict(schema=1,issuer='Meteo-France RSMC La Reunion',source=URL,checked_at=iso(now),status='unavailable',bulletins=[])
    try:
        req=urllib.request.Request(URL,headers={'User-Agent':'InsideMauritiusCycloneWatch/1.0','Accept':'text/html'})
        with urllib.request.urlopen(req,timeout=15) as r:
            if r.geturl()!=URL or r.status!=200:raise ValueError('Unexpected response')
            body=r.read(2_000_001)
            if len(body)>2_000_000:raise ValueError('Oversize')
        parser=PageText();parser.feed(body.decode('utf-8','replace'))
        out['bulletins']=parse(' '.join(parser.parts),now)
        out['status']='ok' if out['bulletins'] else 'no_verified_forecast'
    except Exception as e:print('Forecast unavailable:',type(e).__name__)
    pathlib.Path('official-forecast.json').write_text(json.dumps(out,indent=2))
    print('Official forecast:',out['status'],'bulletins:',len(out['bulletins']))
if __name__=='__main__':main()
