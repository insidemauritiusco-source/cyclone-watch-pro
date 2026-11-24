"""Archive verified structured MMS observations and warning summaries, independently of update.py."""
import json, pathlib, hashlib
ROOT=pathlib.Path(__file__).resolve().parent
target=ROOT/'archive.json'
data=json.loads((ROOT/'data.json').read_text())
old=json.loads(target.read_text()) if target.exists() else {'schema':1,'observations':[],'bulletins':[]}
obs=old['observations']; bulletins=old['bulletins']
def signature(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:24]
known={x['id'] for x in obs}
def add_observation(s,checked):
    if not isinstance(s,dict) or not s.get('observed') or not s.get('name'): return
    if not isinstance(s.get('lat'),(int,float)) or not isinstance(s.get('lon'),(int,float)): return
    if not (-90<=s['lat']<=90 and -180<=s['lon']<=180): return
    record={k:s.get(k) for k in ('name','observed','lat','lon','pressure','speed','direction','wind')}
    key=signature(record)
    if key not in known:
        obs.append(dict(record,id=key,archived_at=checked));known.add(key)
if data.get('source_status')=='ok':
    for s in data.get('history',[]): add_observation(s,data.get('checked_at'))
    add_observation(data.get('storm'),data.get('checked_at'))
    storm=data.get('storm')
    entry={'storm':storm,'warning':data.get('warning'),'source_status':'ok'}
    key=signature(entry)
    if not bulletins or bulletins[-1]['id']!=key:
        bulletins.append(dict(entry,id=key,checked_at=data.get('checked_at')))
    old['last_successful_check']=data.get('checked_at')
old['source']='Mauritius Meteorological Services'
old['storm_url']='https://metservice.intnet.mu/current-cyclone.php'
old['warning_url']='https://metservice.intnet.mu/tropical-cyclone/current-cyclone.php'
old['archive_note']='Structured summaries only; observations are not forecasts. Source check time is not observation time. Retains up to 5000 observations and bulletin changes.'
old['observations']=obs[-5000:]
old['bulletins']=bulletins[-5000:]
temp=target.with_suffix('.tmp')
temp.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n')
temp.replace(target)
print('Archive entries:',len(old['observations']),len(old['bulletins']))
