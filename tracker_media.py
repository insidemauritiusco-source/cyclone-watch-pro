"""Stage real timestamped regional satellite frames for the independent tracker."""
import datetime as dt, hashlib, json, pathlib, sys
from geo_satellite import BASE,LAYER,SIZE,request,capabilities,advertised_times,covers,bbox_params,decode
from premium_graphics import enhance,coast_layers
B=(43,83,-29,-4)
def build(out,now,fetch=request,coast=True):
    out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True)
    result={'status':'unavailable','source':BASE,'crs':'EPSG:4326','bounds':B,'frames':[],'coast':None}
    try:
        _,spec,extent=capabilities(fetch(dict(service='WMS',version='1.3.0',request='GetCapabilities',namespace='msg_iodc'),8_000_000),LAYER)
        times=advertised_times(spec,now)
        if not covers(B,extent) or not times:raise ValueError('No verified regional imagery')
        times=[t for t in times if t>=now-dt.timedelta(hours=6)] or times[-1:]
        n=min(6,len(times));times=[times[round(i*(len(times)-1)/(n-1))] for i in range(n)] if n>1 else times[-1:]
        seen=set()
        for stamp in times:
            try:
                im=decode(fetch(bbox_params(B,LAYER,stamp),12_000_000))
                digest=hashlib.sha256(im.tobytes()).hexdigest()
                if digest in seen:continue
                seen.add(digest)
                raw=digest+'-raw.jpg';im.convert('RGB').save(out/raw,quality=91)
                colored,changed=enhance(im);colored_name=None
                if changed:
                    colored_name=digest+'-ir.jpg';colored.convert('RGB').save(out/colored_name,quality=91)
                result['frames'].append({'captured_at':stamp.isoformat(),'sha256':digest,'raw':'tracker-media/'+raw,'enhanced':'tracker-media/'+colored_name if colored_name else None})
            except Exception as e:print('Tracker frame unavailable:',e)
        if result['frames']:result['status']='ok'
    except Exception as e:print('Tracker imagery unavailable:',e)
    if coast:
        try:
            coast_layers({'wide':B},SIZE)['wide'].save(out/'coast.png')
            result['coast']='tracker-media/coast.png'
        except Exception as e:print('Tracker coastlines unavailable:',e)
    (out/'manifest.json').write_text(json.dumps(result,indent=2))
    print('Tracker:',result['status'],len(result['frames']),'real frames')
    return result
if __name__=='__main__':build(sys.argv[1],dt.datetime.now(dt.timezone.utc))
