import datetime as dt
from official_forecast import parse,UTC
# Synthetic bulletin format fixture, never published as live data.
sample='''WTIO20 FMEE 240000
ISSUED BY METEO-FRANCE/TROPICAL CYCLONE CENTER/LA REUNION 24/11/2026 AT 0000 UTC.
WARNING NUMBER: 003/3 (SOUTH-WEST INDIAN OCEAN)
BEGINNING OF VALIDITY: TUESDAY 24/11/2026 AT 0000 UTC.
POSITION: WITHIN 30 NM RADIUS OF POINT 9.5 S / 77.1 E
FORECAST POSITION AND INTENSITY:
12H, VALID 2026/11/24 AT 12 UTC: 10.5 S / 76.4 E
24H, VALID 2026/11/25 AT 00 UTC: 11.4 S / 75.8 E
OTHER INFORMATION: NIL='''
now=dt.datetime(2026,11,24,10,tzinfo=UTC)
r=parse(sample,now)
assert len(r)==1 and r[0]['system_number']==3
assert [p['hours'] for p in r[0]['points']]==[12,24]
assert parse(sample.replace('FMEE','FIMP'),now)==[]
assert parse(sample,now+dt.timedelta(days=2))==[]
assert parse(sample.replace('AT 12 UTC','AT 13 UTC'),now)[0]['points'][0]['hours']==24
print('PASS official forecast parser: attribution, lead time and expiry checks')
