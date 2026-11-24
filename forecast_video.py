"""Forecast data used for dated video drafts; never derive future coordinates."""
import datetime as dt, json, re, math
from pathlib import Path
from official_forecast import URL
UTC=dt.timezone.utc
MUT=dt.timezone(dt.timedelta(hours=4))
def timestamp(s):
    try:
        x=dt.datetime.fromisoformat(s)
        return x if x.tzinfo is not None else None
    except (TypeError,ValueError):return None
def recent(s,now,seconds):
    x=timestamp(s)
    return x is not None and -300<=(now-x).total_seconds()<=seconds
def inside(p):
    return isinstance(p,dict) and all(type(p.get(k)) in (int,float) and math.isfinite(p[k]) for k in ('lat','lon')) and -45<=p['lat']<0 and 30<=p['lon']<=90
def select_forecast(d,feed,now):
    if d.get('source_status')!='ok' or not recent(d.get('checked_at'),now,2700):return None
    s=d.get('storm') or {};m=re.search(r'\bB0*(\d{1,2})\b',str(s.get('name','')),re.I)
    if not m or not inside(s) or not isinstance(feed,dict) or feed.get('schema')!=1 or feed.get('source')!=URL or feed.get('issuer')!='Meteo-France RSMC La Reunion' or feed.get('status')!='ok' or not recent(feed.get('checked_at'),now,2700):return None
    candidates=[]
    for b in feed.get('bulletins') or []:
        if not isinstance(b,dict) or b.get('system_number')!=int(m[1]) or type(b.get('bulletin_number')) is not int or not inside(b.get('anchor')) or not recent(b.get('issued_at'),now,86400):continue
        pts=b.get('points');issued=timestamp(b['issued_at'])
        if not isinstance(pts,list) or not pts:continue
        last=0;valid=True
        for p in pts:
            if not inside(p) or type(p.get('hours')) is not int or not last<p['hours']<=120 or timestamp(p.get('valid_at'))!=issued+dt.timedelta(hours=p['hours']):valid=False;break
            last=p['hours']
        if valid and any(timestamp(p['valid_at'])>now for p in pts):candidates.append(b)
    return max(candidates,key=lambda b:(timestamp(b['issued_at']),b['bulletin_number']),default=None)
def load_forecast(d,root,now=None):
    try:return select_forecast(d,json.loads((Path(root)/'official-forecast.json').read_text()),now or dt.datetime.now(UTC))
    except (OSError,ValueError,TypeError,KeyError):return None
def local_time(s):
    x=timestamp(s)
    return x.astimezone(MUT).strftime('%d/%m/%Y %H:%M MUT') if x else '—'
def spoken_time(s,language):
    x=timestamp(s).astimezone(MUT)
    if language=='fr':
        months=['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']
        return f"le {x.day} {months[x.month-1]} à {x.hour} heures"+(f" {x.minute}" if x.minute else "")+", heure de Maurice"
    return f"le {x.day}/{x.month}, {x.hour} er"+(f" {x.minute}" if x.minute else "")+", ler Moris"
def forecast_words(b,language):
    if not b:return "Aucune trajectoire prévisionnelle officielle correspondante n'est disponible." if language=='fr' else "Pena trajektwar previzionel ofisiel verifie."
    start=spoken_time(b['issued_at'],language)
    if language=='fr':
        sentences=[f"Prévisions de Météo-France, bulletin émis {start}."]
        for p in b['points']:
            sentences.append(f"À plus {p['hours']} heures, position prévue {spoken_time(p['valid_at'],language)}.")
        sentences.append("Ces points jaunes sont des prévisions incertaines, pas des observations ni une prévision d'impact sur Maurice.")
    else:
        sentences=[f"Previzion Meteo France, bilten emet {start}."]
        for p in b['points']:
            sentences.append(f"A plis {p['hours']} er, pozision prevwar {spoken_time(p['valid_at'],language)}.")
        sentences.append("Bann pwin zonn se previzion insertin, pa observasion ni enn previzion limpakt lor Moris.")
    return ' '.join(sentences)

def zoom_bounds(points):
    """Stable close-up for the entire issued track, not a forecast computation."""
    if not points or not all(inside(p) for p in points):raise ValueError('Invalid zoom positions')
    xs=[p['lon'] for p in points];ys=[p['lat'] for p in points]
    cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
    dx=max(2.4,(max(xs)-min(xs))*1.65);dy=max(2.4,(max(ys)-min(ys))*1.65)
    # Equal degrees per pixel on the schematic 900 x 570 plotting area.
    dx=max(dx,dy*900/570);dy=max(dy,dx*570/900)
    return cx-dx/2,cx+dx/2,cy-dy/2,cy+dy/2

def scene_holds(count,forecast_count,audio_duration,labels):
    """Legacy test helper for the unzoomed sequence."""
    if not forecast_count:return [audio_duration/count]*count
    boundary=next((a for a,_,s in labels if s.startswith(('Prévisions de Météo-France','Previzion Meteo France'))),audio_duration*.65)
    boundary=max(audio_duration*.15,min(audio_duration*.85,boundary))
    return [boundary/count]*count+[(audio_duration-boundary)/forecast_count]*forecast_count

def zoom_scene_holds(count,points,duration,labels):
    """Overview at the forecast introduction, then each point at its spoken cue.
    End of last point is held through the closing safety narration."""
    if not points:return [duration/count]*count
    intro=next((a for a,_,s in labels if s.startswith(('Prévisions de Météo-France','Previzion Meteo France'))),None)
    cues=[]
    for p in points:
        prefixes=(f"À plus {p['hours']} heures,",f"A plis {p['hours']} er,")
        cues.append(next((a for a,_,s in labels if s.startswith(prefixes)),None))
    if intro is None or any(c is None for c in cues) or not 0<intro<cues[0] or any(b<=a for a,b in zip(cues,cues[1:])) or cues[-1]>=duration:
        raise ValueError('Forecast narration cue missing or out of order')
    holds=[intro/count]*count+[cues[0]-intro]
    for a,b in zip(cues,cues[1:]+[duration]):
        holds.extend([(b-a)/2,(b-a)/2])
    return holds
