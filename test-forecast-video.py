import datetime as dt
from forecast_video import select_forecast,forecast_words,scene_holds,zoom_scene_holds,zoom_bounds,URL
from broadcast_gate import report_key
from tv_layout import render_card
from PIL import Image
now=dt.datetime(2026,11,24,10,tzinfo=dt.timezone.utc)
iso=lambda x:x.isoformat()
d={'source_status':'ok','checked_at':iso(now),'storm':{'name':'Tropical Depression (B03)','lat':-9.7,'lon':76.8}}
issue=now-dt.timedelta(hours=6)
p={'lat':-10.5,'lon':76.4,'hours':12,'valid_at':iso(issue+dt.timedelta(hours=12)),'max_wind_kt':30}
q={'lat':-11.4,'lon':75.8,'hours':24,'valid_at':iso(issue+dt.timedelta(hours=24))}
b={'system_number':3,'bulletin_number':2,'issued_at':iso(issue),'anchor':{'lat':-9.5,'lon':77.1},'points':[p,q]}
f={'schema':1,'issuer':'Meteo-France RSMC La Reunion','source':URL,'status':'ok','checked_at':iso(now),'bulletins':[b]}
assert select_forecast(d,f,now)==b
assert select_forecast({**d,'storm':{**d['storm'],'name':'B04'}},f,now) is None
assert select_forecast(d,f,now+dt.timedelta(hours=2)) is None
assert select_forecast(d,{**f,'bulletins':[{**b,'points':[{**p,'valid_at':iso(now)}]}]},now) is None
assert report_key(d,b)!=report_key(d,None)
assert '24 heures' in forecast_words(b,'fr')
assert abs(sum(scene_holds(4,2,60,[(40,45,'Prévisions de Météo-France')]))-60)<.01
values=dict(name='TEST — NOT AN OFFICIAL BULLETIN',obs='Test',fresh=True,pressure='—',speed='—',distance='—',direction='—',coord='—',warning='Non vérifié',checked='Test',track=[{'lat':-9.7,'lon':76.8,'observed':'Test'}],bearing='southsouthwest',forecast=b)
for lang in ('fr','mfe'):
    card=render_card(lang,values,Image.new('RGB',(800,600),'#23556f'),'Test',1,1)
    assert card.size==(2160,3840)
    for i in range(2):
        card=render_card(lang,values,None,'',1,i+2,forecast_step=i)
        assert card.size==(2160,3840)
        # Verify actual forecast point color appears in the expanded map.
        assert any(n>100 and rgb==(255,218,114) for n,rgb in card.crop((72,620,2088,2360)).getcolors(1000000))
print('PASS forecast video: matched official points, expiry, timed scenes, 4K forecast graphics and report key')

# Verify source coordinates remain unchanged, and zoom fits all published points.
import copy
original=copy.deepcopy(b)
lo,hi,south,north=zoom_bounds([b['anchor'],p,q,values['track'][0]])
assert hi-lo<10 and north-south<10
assert all(lo<x['lon']<hi and south<x['lat']<north for x in [b['anchor'],p,q])
assert b==original
labels=[(35,39,'Prévisions de Météo-France'),(39,44,'À plus 12 heures, position prévue'),(44,49,'À plus 24 heures, position prévue')]
holds=zoom_scene_holds(4,[p,q],60,labels)
assert len(holds)==9 and abs(sum(holds)-60)<.001
assert abs(sum(holds[:5])-39)<.001 and abs(sum(holds[:7])-44)<.001
try:
    zoom_scene_holds(4,[p,q],60,labels[:2]);raise AssertionError('Missing speech cue accepted')
except ValueError:pass
for lang in ('fr','mfe'):
    for step,zoom in [(-1,False),(0,True),(1,True)]:
        card=render_card(lang,values,None,'',1,step+2,forecast_step=step,forecast_zoom=zoom)
        assert card.size==(2160,3840)
assert b==original
print('PASS forecast auto zoom, regional inset, source coordinates unchanged and individual narration cues')
