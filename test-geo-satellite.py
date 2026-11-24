"""Synthetic test-only rasters, never included in production reports."""
import datetime as dt, io
from PIL import Image,ImageDraw
from geo_satellite import *
from tv_layout import render_card
now=dt.datetime(2026,11,24,12,tzinfo=UTC)
bb=(43,83,-29,-4)
assert bbox_params(bb,LAYER,now)['bbox']=='-29,43,-4,83'
assert pixel(bb,-4,43)==(0,0)
assert pixel(bb,-29,83)==SIZE
assert pixel(bb,-16.5,63)==(900,570)
caps=b'''<WMS_Capabilities version="1.3.0"><Capability><Layer><CRS>EPSG:4326</CRS><Layer><Name>msg_iodc:ir108</Name><Dimension name="time">2026-11-24T06:00:00Z/2026-11-24T12:00:00Z/PT1H</Dimension><EX_GeographicBoundingBox><westBoundLongitude>20</westBoundLongitude><eastBoundLongitude>100</eastBoundLongitude><southBoundLatitude>-50</southBoundLatitude><northBoundLatitude>30</northBoundLatitude></EX_GeographicBoundingBox></Layer></Layer></Capability></WMS_Capabilities>'''
_,times,extent=capabilities(caps,LAYER)
assert len(advertised_times(times,now))==6
assert advertised_times(times,now)[-1].hour==11
assert covers(bb,extent)
try:capabilities(caps.replace(b'EPSG:4326',b'EPSG:3857'),LAYER);raise AssertionError('Wrong CRS accepted')
except ValueError:pass
def fake(params,limit):
    if params['request']=='GetCapabilities':
        if params.get('namespace')=='overlay':raise ValueError('No coast layer in fixture')
        return caps
    # Vary image contents with advertised time so dedupe can be verified.
    n=int(params['time'][11:13])
    im=Image.new('RGBA',SIZE,(60+n,80,120,255))
    ImageDraw.Draw(im).rectangle((0,0,899,1139),fill=(170,180,190,255))
    out=io.BytesIO();im.save(out,'PNG');return out.getvalue()
p={'lat':-9.7,'lon':76.8,'observed':'24 November 2026 10 AM','name':'Tropical Depression (B03)','direction':'South Southwest'}
b={'system_number':3,'bulletin_number':1,'issued_at':'2026-11-24T06:00:00Z','anchor':{'lat':-9.5,'lon':77.1},'points':[{'hours':12,'valid_at':'2026-11-24T18:00:00Z','lat':-10.8,'lon':76.6}]}
data={'storm':p}
meta,images=build(data,b,now,fake)
assert meta['status']=='ok' and len(images)==4 and meta['coastline'] is None
extended,extended_images=build(data,b,now,fake,max_frames=15)
assert len(extended_images)==6 and len({f['sha256']['wide'] for f in extended['frames']})==6
assert all(x['captured_at'] for x in meta['frames'])
def bad(params,limit):raise ValueError('network unavailable')
assert build(data,b,now,bad)[0]['status']=='unavailable'
assert build(data,None,now,fake)[0]['status']=='unavailable'
from tv_layout import observed_track
vals=dict(name='TEST ONLY',obs='TEST',fresh=True,pressure='—',speed='—',distance='—',direction='—',coord='—',warning='TEST',checked='TEST',track=observed_track(data),bearing=p['direction'],forecast=b)
stamp=list(images)[0]
sm={'bounds':meta['bounds']['close'],'image':images[stamp]['close'],'captured':'TEST UTC','credit':meta['credit']}
card=render_card('fr',vals,None,'',0,0,forecast_step=0,forecast_zoom=True,satellite_map=sm)
assert card.size==(2160,3840)
# The outer edges of the map contain coordinate labels and grid lines.
# Verify the actual satellite raster across both halves rather than a
# single pixel that may legitimately be overdrawn by map annotations.
def raster_agreement(card,source):
    matches=0;total=0
    for y in range(30,1110,19):
        for x in range(30,1770,23):
            total+=1
            matches+=card.getpixel((172+x,790+y))==source.getpixel((x,y))
    return matches/total
assert raster_agreement(card,sm['image'])>.8, 'Aligned satellite raster absent or displaced'
# Verify projected forecast center independently of background agreement.
point=b['points'][0]
x,y=pixel(sm['bounds'],point['lat'],point['lon'])
assert card.getpixel((172+round(x),790+round(y)))==(255,218,114), 'Forecast point not at projected coordinate'
fallback=render_card('fr',vals,None,'',0,0,forecast_step=0,forecast_zoom=True,satellite_map=dict(sm,bounds=bb))
assert raster_agreement(fallback,sm['image'])<.05, 'Mismatched projection must use schematic fallback'
print('PASS georeferenced satellite: WMS axis order, exact advertised times, coverage, source fallback and raster placement')
