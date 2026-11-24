"""Decide whether a verified observation/warning needs a new video draft."""
import hashlib,json,os,pathlib,datetime,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parent
def fingerprint(d):
    payload={'storm':d.get('storm'),'warning':d.get('warning')}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def current(d):
    try:
        age=(datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(d['checked_at'])).total_seconds()
        return d.get('source_status')=='ok' and -300<=age<=2700 and bool(d.get('warning'))
    except (ValueError,KeyError,TypeError):return False
def main():
    d=json.loads((ROOT/'data.json').read_text()); key=fingerprint(d)
    render=True;reason='Manual or code-triggered report'
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
                            previous=json.loads(f.read_text()).get('observation_key');break
                render=previous!=key;reason='New verified observation or warning' if render else 'Already rendered this observation and warning'
            except Exception as e:
                # No repeated expensive renders when GitHub is unavailable.
                reason='Could not verify previous report: '+str(e)
    print(reason)
    with open(os.environ['GITHUB_OUTPUT'],'a') as out:out.write('render='+str(render).lower()+'\n')
if __name__=='__main__':main()
