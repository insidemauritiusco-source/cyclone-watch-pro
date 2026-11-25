"""List retained video artifacts, newest first, no external publication."""
import json,os,subprocess,pathlib
repo=os.environ['GITHUB_REPOSITORY']
items=[]
try:
    raw=subprocess.check_output(['gh','api','repos/'+repo+'/actions/artifacts?name=Inside-Mauritius-V31-Reviewed-Draft&per_page=100'],text=True,timeout=30)
    for a in json.loads(raw).get('artifacts',[]):
        w=a.get('workflow_run') or {}
        if a.get('expired') or w.get('head_branch')!='main':continue
        run=w.get('id')
        if not isinstance(run,int):continue
        # Only link retained artifacts; do not call them social-approved.
        items.append({'run':run,'created_at':a.get('created_at'),'expires_at':a.get('expires_at'),'url':f'https://github.com/{repo}/actions/runs/{run}','status':'review_required'})
except Exception as e: print('Archive unavailable:',e)
items.sort(key=lambda a:a.get('created_at') or '',reverse=True)
pathlib.Path('broadcast-archive.json').write_text(json.dumps({'reports':items,'retention':'Up to 30 days; sign in to GitHub to download archived artifacts.'},indent=2))
pathlib.Path('broadcast-runs.txt').write_text(''.join(str(a['run'])+'\n' for a in items[:3]))
