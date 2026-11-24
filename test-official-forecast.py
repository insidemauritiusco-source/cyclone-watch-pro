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

# Synthetic format examples: missing intensity must not borrow from next point.
with_wind=sample.replace('10.5 S / 76.4 E','10.5 S / 76.4 E, MAX WIND = 30 KT, TROPICAL DEPRESSION').replace('11.4 S / 75.8 E','11.4 S / 75.8 E, MAX WIND = 40 KT, MODERATE TROPICAL STORM')
a=parse(with_wind,now)[0]['points']
assert a[0]['max_wind_kt']==30 and a[0]['classification']=='TROPICAL DEPRESSION'
assert a[1]['max_wind_kt']==40 and a[1]['classification']=='MODERATE TROPICAL STORM'
assert 'max_wind_kt' not in parse(sample,now)[0]['points'][0]
assert 'max_wind_kt' not in parse(with_wind.replace('MAX WIND = 30 KT','MAX WIND = 999 KT'),now)[0]['points'][0]
print('PASS per-point forecast wind and classification, missing values remain missing')
