"""Check official public bulletin page reachability; never derive warning status."""
import datetime as dt,json,pathlib,urllib.request,urllib.parse,concurrent.futures
ROOT=pathlib.Path(__file__).resolve().parent
SOURCES={
 'mauritius':'https://metservice.intnet.mu/cyclone-bulletin-english-mauritius.php',
 'rodrigues':'https://metservice.intnet.mu/cyclone-bulletin-english-rodrigues.php',
 'reunion':'https://meteofrance.re/fr/cyclone',
 'reunion_vigilance':'https://vigilance.meteofrance.fr/fr/la-reunion'}
def check(item):
    name,url=item; state='unavailable'
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'InsideMauritiusCycloneWatch/1.0','Accept':'text/html'})
        with urllib.request.urlopen(req,timeout=12) as r:
            final=urllib.parse.urlsplit(r.geturl())
            initial=urllib.parse.urlsplit(url)
            if final.scheme=='https' and final.hostname==initial.hostname and r.status==200 and 'text/html' in r.headers.get('Content-Type','').lower():
                body=r.read(65536)
                if len(body)>500:state='page_reachable'
    except Exception:pass
    return {'id':name,'status':state,'checked_at':dt.datetime.now(dt.timezone.utc).isoformat()}
def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(check,SOURCES.items()))
    out=ROOT/'regional-sources.json';tmp=out.with_suffix('.tmp')
    tmp.write_text(json.dumps({'schema':1,'checked_at':dt.datetime.now(dt.timezone.utc).isoformat(),'meaning':'HTTP page reachability only; not verified meteorological content','sources':rows},indent=2))
    tmp.replace(out)
    print('V22 regional source reachability:',[(x['id'],x['status']) for x in rows])
if __name__=='__main__':main()
