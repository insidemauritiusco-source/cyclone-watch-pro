from premium_graphics import *
import datetime as dt
from PIL import Image
# Synthetic test images, never published.
src=Image.new('RGBA',(256,1))
for i in range(256):src.putpixel((i,0),(i,i,i,123))
out,yes=enhance(src)
assert yes and out.size==src.size and out.getpixel((0,0))==(*palette_rgb(0),123)
assert out.getpixel((255,0))==(*palette_rgb(255),123)
rgb=Image.new('RGBA',(2,2),(10,20,30,255));other,yes=enhance(rgb)
assert not yes and other.tobytes()==rgb.tobytes()
bb=(43,83,-29,-4)
assert clip_segment((40,-10),(45,-10),bb)==((43.,-10.),(45.,-10.))
assert clip_segment((0,0),(2,2),bb) is None
fixture={'type':'FeatureCollection','features':[{'geometry':{'type':'LineString','coordinates':[[57,-20],[58,-20],[58,-21]]}}]}
coasts=coast_layers({'wide':bb,'close':(75,79,-12,-8)},(180,114),lambda _:fixture)
assert coasts['wide'].getchannel('A').getbbox()
assert not coasts['close'].getchannel('A').getbbox()
assert satellite_time_label('2026-11-24T22:00:00+00:00')=='24/11/2026 22:00 UTC | 25/11/2026 02:00 MUT'
frame=fullscreen_frame(out.resize((1800,1140)),'2026-11-24T12:00:00+00:00','TEST',True,1,2)
assert frame.size==(3840,2160)
print('PASS Premium graphics: fixed brightness palette, source geometry, clipped coastline, UTC/MUT timestamps and 4K full-screen layout')
