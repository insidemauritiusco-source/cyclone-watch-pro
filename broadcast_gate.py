"""Decide whether a verified observation/warning needs a new video draft."""
import hashlib,json,os,pathlib,datetime,subprocess,tempfile,re,math
ROOT=pathlib.Path(__file__).resolve().parent
def fingerprint(d):
    payload={'storm':d.get('storm'),'warning':d.get('warning')}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def report_key(d,forecast):
    return hashlib.sha256(json.dumps({'observation':fingerprint(d),'forecast':forecast},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def current(d,now=None):
    try:
        age=((now or datetime.datetime.now(datetime.timezone.utc))-datetime.datetime.fromisoformat(d['checked_at'])).total_seconds()
        if not (d.get('source_status')=='ok' and -300<=age<=2700 and d.get('errors')==[] and re.fullmatch(r'No warning reported|Class (I|II|III|IV)',d.get('warning',''))): return False
        s=d.get('storm')
        return s is None or (isinstance(s,dict) and isinstance(s.get('name'),str) and bool(s['name'].strip()) and s['name']!='Reported tropical system (name unverified)' and isinstance(s.get('observed'),str) and bool(s['observed'].strip()) and all(type(s.get(k)) in (int,float) and math.isfinite(s[k]) for k in ('lat','lon')) and -45<=s['lat']<0 and 30<=s['lon']<=90)
    except (ValueError,KeyError,TypeError):return False
def main():
    from forecast_video import load_forecast
    d=json.loads((ROOT/'data.json').read_text()); key=report_key(d,load_forecast(d,ROOT))
    render=current(d);reason='Verified manual or code-triggered report' if render else 'Blocked before render: official observation or warning unavailable or stale'
    if os.environ.get('GITHUB_EVENT_NAME')=='schedule':
        render=False;reason='No verified fresh source'
        if current(d):
            # Only inspect successful artifacts from the trusted video workflow.
            try:
                raw=subprocess.check_output(['gh','api','repos/'+os.environ['GITHUB_REPOSITORY']+'/actions/artifacts?name=Inside-Mauritius-Broadcast-Manifest&per_page=20'],text=True,timeout=30)
                runs=[{'databaseId':a['workflow_run']['id']} for a in json.loads(raw).get('artifacts',[]) if not a.get('expired') and a.get('workflow_run',{}).get('head_branch')=='main']
                previous=None
                for run in runs:
                    with tempfile.TemporaryDirectory() as folder:
                        p=subprocess.run(['gh','run','download',str(run['databaseId']),'--name','Inside-Mauritius-Broadcast-Manifest','--dir',folder],capture_output=True,text=True,timeout=20)
                        if p.returncode:continue
                        f=pathlib.Path(folder)/'source.json'
                        if f.exists():
                            previous=json.loads(f.read_text()).get('report_key');break
                render=previous!=key;reason='New verified observation, warning or forecast' if render else 'Already rendered this observation, warning and forecast'
            except Exception as e:
                # No repeated expensive renders when GitHub is unavailable.
                reason='Could not verify previous report: '+str(e)
    print(reason)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as summary: summary.write('V31.1 pre-render gate: '+('eligible' if render else 'skipped')+' — '+reason+'\n')
    with open(os.environ['GITHUB_OUTPUT'],'a') as out:out.write('render='+str(render).lower()+'\n')
if __name__=='__main__':main()
