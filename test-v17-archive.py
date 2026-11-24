import datetime as dt
from satellite_archive import merge,product
now=dt.datetime(2026,11,24,12,tzinfo=dt.timezone.utc)
def frame(hours,kind='IR'):
    return {'url':'https://metservice.intnet.mu/mmsimages/2026-11-24_10%3A00%3A00_'+kind+'%20Meteosat-9%202026-11-24%200600.jpg','captured_at':(now-dt.timedelta(hours=hours)).isoformat()}
a,b=frame(1),frame(2)
invalid=dict(a,url='https://example.com/mmsimages/bad.jpg')
r=merge({'frames':[a,frame(200)]},{'frames':[a,b,invalid,frame(1,'VIS')]},now)
assert len(r)==3 and r[0]['captured_at']==b['captured_at']
assert len({x['product'] for x in r})==2
assert len(merge({'frames':r},{},now))==3
print('PASS V17 archive: retention, chronology, duplicate removal, host validation, product separation')
