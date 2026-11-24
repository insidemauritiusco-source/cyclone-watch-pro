"""Local 4K narration replacement. No network calls, no upload. Python + FFmpeg required.
Usage: python voice-remux.py weather-mfe.mp4 approved-recording.wav output.mp4
Only use recordings you have permission to use, matching the dated weather report.
"""
import sys,subprocess,pathlib,json,math
if len(sys.argv)!=4:raise SystemExit(__doc__)
video,audio,out=map(pathlib.Path,sys.argv[1:])
if out.exists() or out.resolve() in [video.resolve(),audio.resolve()]:raise SystemExit('Choose a new output file.')
def probe(p):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
info=probe(video);vs=next((s for s in info['streams'] if s['codec_type']=='video'),{})
if (vs.get('width'),vs.get('height'))!=(2160,3840):raise SystemExit('Source is not vertical 4K.')
vd=float(info['format']['duration']);ad=float(probe(audio)['format']['duration'])
if not math.isfinite(ad) or ad<=0 or abs(vd-ad)>0.5:raise SystemExit('Recording must match video length within half a second. Edit the recording first; no words will be cut automatically.')
subprocess.run(['ffmpeg','-n','-i',str(video),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','160k','-af','apad','-t',f'{vd:.6f}','-movflags','+faststart',str(out)],check=True)
print('Saved local 4K MP4. Original captions omitted because recording timing may differ.')
