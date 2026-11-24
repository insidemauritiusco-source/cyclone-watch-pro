"""Archive published MMS satellite URLs and source-check outcomes, not copied imagery."""
import datetime as dt, json, pathlib, re, urllib.parse
ROOT=pathlib.Path(__file__).resolve().parent
UTC=dt.timezone.utc
def read(path,default):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return default
def stamp(s):
    try:
        t=dt.datetime.fromisoformat(s)
        return t.astimezone(UTC) if t.tzinfo is not None else None
    except (ValueError,TypeError):return None
def product(url):
    n=urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit('/',1)[-1])
    n=re.sub(r'^20\d{2}-\d{2}-\d{2}_[^_]+_', '',n)
    return re.sub(r'\s+20\d{2}-\d{2}-\d{2}\s+\d{4}.*$', '',n).strip().lower()
def valid(f,now):
    if not isinstance(f,dict):return None
    try:
        url=f['url'];p=urllib.parse.urlsplit(url);t=stamp(f['captured_at'])
        if p.scheme!='https' or p.hostname!='metservice.intnet.mu' or p.port not in (None,443) or p.username or p.password or not p.path.startswith('/mmsimages/') or '..' in urllib.parse.unquote(p.path).split('/') or not re.search(r'\.(jpg|jpeg|png|webp)$',p.path,re.I):return None
        if t is None or not -600<=(now-t).total_seconds()<=7*86400:return None
        return {'url':url,'captured_at':t.isoformat(),'product':product(url)}
    except (KeyError,TypeError,ValueError):return None
def merge(old,media,now):
    pool=list(old.get('frames',[]))+list(media.get('replay',[]))+list(media.get('frames',[]))
    if media.get('satellite'):pool.append(media['satellite'])
    for layer in media.get('layers',{}).values():pool.extend(layer.get('frames',[]))
    unique={}
    for f in pool:
        x=valid(f,now)
        if x:unique[(x['product'],x['captured_at'])]=x
    return sorted(unique.values(),key=lambda x:x['captured_at'])[-2500:]
def write(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)
def main():
    now=dt.datetime.now(UTC); target=ROOT/'satellite-archive.json'
    old=read(target,{});mp=ROOT/'media.json';m=read(mp,{})
    check=stamp(m.get('checked_at'));current=check is not None and -300<=(now-check).total_seconds()<=900
    if not current:m={}
    frames=merge(old,m,now)
    write(target,{'schema':1,'source':'MMS Meteosat published image links','retention_days':7,'updated_at':now.isoformat(),'frames':frames})
    # Add matching archived frames to the rolling 24-hour replay only when the
    # current product is known. Do not substitute archived data for current source status.
    def matching(p):
        return [{k:f[k] for k in ('url','captured_at')} for f in frames if f['product']==p and (now-stamp(f['captured_at'])).total_seconds()<=86400][-96:]
    if m.get('satellite'):
        m['replay']=matching(product(m['satellite']['url']))
        for layer in m.get('layers',{}).values():
            if layer.get('product'):layer['frames']=matching(layer['product'])
        write(mp,m)
    d=read(ROOT/'data.json',{});checked=stamp(d.get('checked_at'))
    ok=d.get('source_status')=='ok' and checked is not None and -300<=(now-checked).total_seconds()<=2700
    media_ok=bool(m.get('satellite')) and current
    health=read(ROOT/'source-health.json',{})
    events=health.get('events',[])
    state={'bulletin':'retrieved' if ok else 'unverified','satellite':'links_retrieved' if media_ok else 'unavailable'}
    event={'checked_at':now.isoformat(),**state}
    if not events or any(events[-1].get(k)!=v for k,v in state.items()):events.append(event)
    write(ROOT/'source-health.json',{'schema':1,'checked_at':now.isoformat(),**state,'bulletin_checked_at':d.get('checked_at'),'satellite_checked_at':m.get('checked_at'),'last_bulletin_success':d.get('checked_at') if ok else health.get('last_bulletin_success'),'last_satellite_success':m.get('checked_at') if media_ok else health.get('last_satellite_success'),'events':events[-80:]})
    print('V17 satellite archive links:',len(frames),'source health:',state)
if __name__=='__main__':main()
