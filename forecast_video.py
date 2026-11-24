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
    end=b['points'][-1]; start=spoken_time(b['issued_at'],language)
    if language=='fr':
        return f"Prévisions de Météo-France, bulletin émis {start}. Les points jaunes indiquent les positions prévues jusqu'à {end['hours']} heures après l'émission du bulletin. Ce ne sont pas des observations ni une prévision d'impact sur Maurice."
    return f"Previzion Meteo France, bilten emet {start}. Bann pwin zonn indik pozision prevwar ziska {end['hours']} er apre bilten. Sa pa bann observasion ni enn previzion limpakt lor Moris."
def scene_holds(count,forecast_count,audio_duration,labels):
    """Keep actual satellite sequence and start forecast scenes at the spoken forecast section."""
    if not forecast_count:return [audio_duration/count]*count
    boundary=next((a for a,_,s in labels if s.startswith(('Prévisions de Météo-France','Previzion Meteo France'))),audio_duration*.65)
    # Preserve positive holds even with an unexpectedly short script.
    boundary=max(audio_duration*.15,min(audio_duration*.85,boundary))
    return [boundary/count]*count+[(audio_duration-boundary)/forecast_count]*forecast_count
