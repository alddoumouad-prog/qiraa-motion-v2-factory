#!/usr/bin/env python3
"""Build a reviewable 28-second Motion V2 draft. All paths are relative to repository root."""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, shutil, subprocess, sys
import urllib.request, urllib.error
from pathlib import Path
import cv2
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw
from scipy.io import wavfile
from scipy.signal import lfilter
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent.parent
WORK=ROOT/'work'; OUTPUT=ROOT/'output'
FPS=30; DURATION=28.0; SOURCE_END=23.5; SR=48000; N=round(DURATION*SR)
FF=imageio_ffmpeg.get_ffmpeg_exe()
TRIM='silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,areverse'
sys.path.insert(0,str(ROOT/'factory'))
import render_motion
import brand_lock
import creative_plan
import framing
import adaptive_motion

VOICE_PROFILE=json.loads((ROOT/'assets/voice/voice_profile.json').read_text(encoding='utf-8'))
VOICE_FILTER=VOICE_PROFILE['voice_processing_filter']


def fail(message):raise ValueError(message)
def run(cmd,**kwargs):return subprocess.run([str(x) for x in cmd],check=True,**kwargs)
def local_path(p):
    path=(ROOT/p).resolve()
    if not path.is_relative_to(ROOT):fail('Paths in spec must remain inside the repository')
    return path

def load_spec(path):
    s=json.loads(Path(path).read_text(encoding='utf-8'))
    for k in ['project_id','source_url','source_offset_seconds','source_credit','location','date','headline_lines','cards','narration','micro','tts','editorial_review','transcript_file']:
        if k not in s:fail('Missing spec field: '+k)
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{1,63}',s['project_id']):fail('project_id must use only lowercase letters, numbers, - and _ (2–64 characters)')
    u=urlparse(s['source_url'])
    if u.scheme not in ('http','https') or not u.netloc:fail('source_url must be an http(s) URL')
    if u.username or u.password:fail('Never put credentials in source_url')
    if not 0<=float(s['source_offset_seconds'])<=86400:fail('Invalid source offset')
    if len(s['headline_lines'])!=3 or len(s['cards'])!=4 or len(s['narration'])!=3 or len(s['micro'])!=2:fail('Require exactly 3 headline lines, 4 cards, 3 narration clips, and 2 micro clips')
    if not re.fullmatch(r'\d{2}\.\d{2}\.\d{4}',s['date']):fail('date must be DD.MM.YYYY')
    if s['tts']['provider'] not in ('pre_recorded','elevenlabs'):
        fail('tts.provider must be pre_recorded for agent-generated approved voice clips, or elevenlabs only with an approved same-identity voice')
    creative_plan.validate(s)
    if not isinstance(s['editorial_review'].get('facts_verified'),bool) or not isinstance(s['editorial_review'].get('source_permission_confirmed'),bool):fail('Editorial review fields must be booleans')
    if not s['editorial_review']['facts_verified']:fail('Editorial facts must be verified before rendering')
    if not s['editorial_review']['source_permission_confirmed']:print('WARNING: source rights are NOT confirmed; output is a draft only',flush=True)
    strings=[s['source_credit'],s['location'],*s['headline_lines']]
    if any(not isinstance(x,str) or not x.strip() or len(x)>90 for x in strings):fail('Metadata/headline text empty or too long')
    if any(len(x)>48 for x in s['headline_lines']):fail('Headline line too long (maximum 48 chars)')
    ids=[e.get('id','') for e in s['narration']+s['micro']]
    if len(set(ids))!=5 or any(not re.fullmatch(r'[a-z0-9_-]{1,48}',x) for x in ids):fail('Clip IDs must be unique lowercase letters, numbers, - or _')
    intervals=[]
    for i,e in enumerate(s['micro']):
        if not e.get('text') or len(e['text'])>45:fail('Micro text must have 1–45 characters')
        start=float(e['start']);end=start+2
        if not 0<float(e['max_seconds'])<2:fail('Micro max_seconds must be greater than 0 and less than 2')
        if start<5.25 or end>SOURCE_END:fail('Micro needs a 2-second clear interval between 5.25 and 23.50')
        if abs(start-float(e['anchor_end']))>.12:fail('Micro must start within 0.12 s after the verified word')
        if start+0.001<float(e['anchor_end']):fail('Micro must not start before its anchor word ends')
        intervals.append((start,end,'micro '+str(i)))
    for i,e in enumerate(s['narration']):
        if not e.get('text') or len(e['text'])>220:fail('Each narration text must have 1–220 characters')
        start=float(e['start']);end=start+float(e['max_seconds'])
        if not 0<=start<end<=SOURCE_END:fail('Narration range outside source')
        intervals.append((start,end,'narration '+str(i)))
    for i,(a,b,label) in enumerate(intervals):
        for c,d,other in intervals[i+1:]:
            if max(a,c)<min(b,d)-0.001:fail(f'Audio windows overlap: {label} and {other}')
    card_intervals=[]
    for c in s['cards']:
        if not c.get('kicker') or not c.get('value') or any(len(c.get(k,''))>75 for k in ('kicker','value','sub')):fail('Invalid or overly long card text')
        a,b=float(c['start']),float(c['end'])
        if not 5.22<=a<b<=SOURCE_END or b-a<0.7:fail('Card range must be at least 0.7 s and lie between 5.22 and 23.5')
        for d,e,label in intervals:
            if label.startswith('micro') and max(a,d)<min(b,e)-.001:fail('Cards cannot obscure a micro capsule')
        for d,e in card_intervals:
            if max(a,d)<min(b,e)-.001:fail('Cards cannot overlap')
        card_intervals.append((a,b))
    tp=local_path(s['transcript_file'])
    if not tp.is_file():fail('Word transcript missing: '+str(tp))
    transcript=json.loads(tp.read_text(encoding='utf-8'))
    words=[w for seg in transcript for w in seg.get('words',[])]
    for e in s['micro']:
        anchor=e['anchor_word'].strip().casefold()
        matches=[w for w in words if str(w.get('word','')).strip(' .,!?،؟:;\n').casefold()==anchor and abs(float(w['end'])-float(s['source_offset_seconds'])-float(e['anchor_end']))<=.12]
        if not matches:fail(f"Anchor {anchor!r} at {e['anchor_end']} not found in word-timed transcript")
    return s


def prepare_source(s,local_source=None):
    WORK.mkdir(exist_ok=True)
    if local_source:
        source=Path(local_source).expanduser().resolve()
        if not source.is_file():fail('Local source not found')
    else:
        dest=WORK/'source.%(ext)s'
        run([sys.executable,'-m','yt_dlp','--no-playlist','--no-progress','--restrict-filenames','--ffmpeg-location',FF,'--merge-output-format','mp4','-f','bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best','-o',str(dest),s['source_url']])
        files=[x for x in WORK.glob('source.*') if x.suffix.lower() in ('.mp4','.mkv','.webm','.mov')]
        if len(files)!=1:fail('Expected exactly one source video')
        source=files[0]
    cap=cv2.VideoCapture(str(source))
    if not cap.isOpened():fail('Cannot decode source video')
    fps=cap.get(cv2.CAP_PROP_FPS) or 0;count=cap.get(cv2.CAP_PROP_FRAME_COUNT);cap.release()
    if fps<=0 or count/fps<float(s['source_offset_seconds'])+SOURCE_END-.05:fail('Source does not provide 23.5 seconds after offset')
    target=WORK/'source_clip.mp4'
    run([FF,'-y','-hide_banner','-loglevel','error','-ss',str(s['source_offset_seconds']),'-i',source,'-t',str(SOURCE_END),'-map','0:v:0','-map','0:a:0?','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',target])
    return target


def decode(path,channels=1,filters=None):
    cmd=[FF,'-hide_banner','-loglevel','error','-i',str(path)]
    if filters:cmd+=['-af',filters]
    cmd+=['-ar',str(SR),'-ac',str(channels),'-f','f32le','-']
    raw=run(cmd,capture_output=True).stdout;x=np.frombuffer(raw,dtype='<f4').copy()
    return x.reshape(-1,channels) if channels>1 else x

def norm(x,db):
    if not len(x) or np.max(np.abs(x))<1e-7:fail('Voice or SFX file is empty/silent')
    return x*(10**(db/20)/float(np.max(np.abs(x))))

def add(dst,x,start):
    i=round(start*SR);n=min(len(x),len(dst)-i)
    if n>0:dst[i:i+n]+=x[:n,None] if x.ndim==1 else x[:n]

def synthesize_elevenlabs(text,path):
    """Use a pre-approved voice ID; never log, commit or embed the API key."""
    api_key=os.environ.get('ELEVENLABS_API_KEY','').strip()
    voice_id=os.environ.get('ELEVENLABS_VOICE_ID','').strip()
    if not api_key or not voice_id:
        fail('ElevenLabs voice is not configured; add ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID securely, or use approved prerecorded clips')
    if not re.fullmatch(r'[A-Za-z0-9_-]{5,100}',voice_id):fail('Invalid ElevenLabs voice ID')
    payload={'text':text,'model_id':'eleven_multilingual_v2','voice_settings':{'stability':0.5,'similarity_boost':0.75,'style':0.0,'use_speaker_boost':True,'speed':1.0}}
    request=urllib.request.Request('https://api.elevenlabs.io/v1/text-to-speech/'+voice_id+'?output_format=mp3_44100_128',
        data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),method='POST',
        headers={'xi-api-key':api_key,'Content-Type':'application/json','Accept':'audio/mpeg'})
    try:
        with urllib.request.urlopen(request,timeout=60) as response:
            audio=response.read(12000001)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'ElevenLabs TTS failed (HTTP {e.code}); verify account, voice ID, permissions and credits') from None
    except (urllib.error.URLError,TimeoutError,OSError):
        raise RuntimeError('ElevenLabs TTS connection failed') from None
    if not 512<=len(audio)<=12000000:fail('ElevenLabs returned an invalid audio response')
    Path(path).write_bytes(audio)


def generate_mix(s,source):
    vox=np.zeros((N,2),np.float64);mic=np.zeros((N,2),np.float64);events=[]
    audio_dir=WORK/'voices';audio_dir.mkdir(exist_ok=True)
    for kind,items in [('narration',s['narration']),('micro',s['micro'])]:
        for e in items:
            if s['tts']['provider']=='pre_recorded':
                if not e.get('audio_file'):fail('pre_recorded clip requires audio_file')
                path=local_path(e['audio_file'])
                if not path.is_file():fail('Missing prerecorded audio: '+str(path))
            else:
                path=audio_dir/(e['id']+'.mp3')
                synthesize_elevenlabs(e['text'],path)
            clean=decode(path,1,TRIM)
            duration=len(clean)/SR
            if duration<=0:fail('Empty narration')
            needed=max(1.0,duration/float(e['max_seconds']))
            tempo=max(needed,float(e.get('tempo',1)))
            # atempo's measured output is not always exactly input_length / tempo.
            # Re-measure and adjust slightly rather than clipping spoken words.
            for attempt in range(3):
                max_tempo=1.6 if creative_plan.validate(s)['mode']=='golden' else 1.25
                if tempo>max_tempo:fail(f"{e['id']} needs {tempo:.2f}x speed; shorten text or expand its window (maximum {max_tempo}x for this profile)")
                fil=TRIM+f',atempo={tempo:.8f},'+VOICE_FILTER
                if kind=='micro':fil+=',highpass=f=350,lowpass=f=3000'
                x=norm(decode(path,1,fil),-5 if kind=='micro' else -3)
                actual=len(x)/SR
                if actual<=float(e['max_seconds'])+.001 and (kind!='micro' or actual<2):break
                tempo*=max(1.01,actual/float(e['max_seconds'])*1.02)
            else:fail(f"Clip {e['id']} exceeds its slot after retiming")
            add(mic if kind=='micro' else vox,x,float(e['start']))
            events.append({'id':e['id'],'kind':kind,'start':e['start'],'duration':actual,'tempo':tempo})
    try:
        bed=decode(source,2,'afade=t=out:st=23.25:d=0.25')
        if not len(bed) or np.max(np.abs(bed))<1e-7:raise ValueError('silent audio')
        bed=norm(bed,-3)
        source_audio_status='audible source audio preserved and ducked'
    except subprocess.CalledProcessError as exc:
        detail=exc.stderr.decode('utf-8','replace') if isinstance(exc.stderr,bytes) else str(exc.stderr)
        if 'does not contain any stream' not in detail.lower() and 'matches no streams' not in detail.lower():
            raise RuntimeError('Source audio decode failed: '+detail[-1000:]) from exc
        print('WARNING: source has no audio stream; using silence as source bed',flush=True)
        source_audio_status='no audio stream: silent source bed'
        bed=np.zeros((round(SOURCE_END*SR),2),np.float32)
    except ValueError:
        print('WARNING: source audio is silent; using silence as source bed',flush=True)
        source_audio_status='silent source audio: silent source bed'
        bed=np.zeros((round(SOURCE_END*SR),2),np.float32)
    bed=np.pad(bed[:N],((0,max(0,N-len(bed))),(0,0)))[:N].astype(np.float64)
    target=np.full(N,-3.0)
    for e in events:
        end=e['start']+(2 if e['kind']=='micro' else e['duration'])
        target[round(e['start']*SR):round(end*SR)]=np.minimum(target[round(e['start']*SR):round(end*SR)],-15 if e['kind']=='micro' else -24)
    alpha=math.exp(-1/(.030*SR));smooth=lfilter([1-alpha],[1,-alpha],target)
    bed*=np.power(10,(smooth+3)/20)[:,None]
    effects=np.zeros((N,2),np.float64)
    recipe=json.loads((ROOT/'assets/sfx/recipe_motion_v2.json').read_text(encoding='utf-8'))
    fx=[]
    for item in recipe['events']:
        name=item['asset'];where=item['at']
        if not re.fullmatch(r'[A-Za-z0-9_]+',name):fail('Invalid SFX asset in recipe')
        if where=='each_card_start':times=[float(c['start']) for c in s['cards']]
        elif where=='each_micro_start':times=[float(m['start']) for m in s['micro']]
        else:times=[float(where)]
        for start in times:
            if not 0<=start<DURATION:fail('Invalid SFX time')
            fx.append((name,start))
            add(effects,norm(decode(ROOT/'assets/sfx'/f'{name}.wav'),float(recipe['peak_dbfs_each_before_master'])),start)
    mixed=np.tanh((bed+vox+mic+effects)*.96)/np.tanh(.96)
    wavfile.write(WORK/'mix_premaster.wav',SR,mixed.astype(np.float32))
    run([FF,'-y','-hide_banner','-loglevel','error','-i',WORK/'mix_premaster.wav','-af','loudnorm=I=-14:TP=-1.5:LRA=11','-ar',str(SR),'-ac','2','-c:a','pcm_s24le',WORK/'mix_master.wav'])
    return events,source_audio_status,fx


def qa(s,video,events,source_audio_status,sfx_events,plan,frame_analysis):
    run([FF,'-v','error','-i',video,'-f','null','-'])
    cap=cv2.VideoCapture(str(video));fps=cap.get(cv2.CAP_PROP_FPS);frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT));cap.release()
    if (width,height,frames,round(fps,3))!=(1080,1920,840,30.0):fail('Output format mismatch')
    times=[.5,1.35,3.0]+[float(x['start'])+.6 for x in s['micro']]+[float(x['start'])+.7 for x in s['cards']]+[24.1,26.2]
    times=sorted(set(round(x,2) for x in times))
    contact=Image.new('RGB',(270*4,520*math.ceil(len(times)/4)),(28,28,30));d=ImageDraw.Draw(contact)
    for i,t in enumerate(times):
        dest=WORK/f'qa_{i:02}.jpg'
        run([FF,'-y','-hide_banner','-loglevel','error','-ss',str(t),'-i',video,'-frames:v','1','-q:v','2',dest])
        im=Image.open(dest);im.thumbnail((270,480));x=(i%4)*270;y=(i//4)*520
        contact.paste(im,(x,y));d.text((x+8,y+486),f'{t:.2f} s',fill='white')
    contact.save(OUTPUT/'contact_sheet.jpg',quality=94)
    p=run([FF,'-hide_banner','-nostats','-i',video,'-map','0:a:0','-af','ebur128=peak=true','-f','null','-'],capture_output=True,text=True)
    (OUTPUT/'loudness.txt').write_text(p.stderr[-4000:],encoding='utf-8')
    report={'project_id':s['project_id'],'brand_profile':'qiraa-motion-v2-golden-1','frames':frames,'fps':fps,'width':width,'height':height,'duration_seconds':frames/fps,'source_audio_status':source_audio_status,'voice_provider':s['tts']['provider'],'voice_id_fingerprint':hashlib.sha256(os.environ.get('ELEVENLABS_VOICE_ID','').encode()).hexdigest()[:16] if s['tts']['provider']=='elevenlabs' and os.environ.get('ELEVENLABS_VOICE_ID') else None,'audio_events':events,'sfx_events':[{'asset':name,'start':start} for name,start in sfx_events],'video_sha256':hashlib.sha256(video.read_bytes()).hexdigest(),'facts_verified_by_editor':s['editorial_review']['facts_verified'],'source_permission_confirmed':s['editorial_review']['source_permission_confirmed'],'publication_status':'DRAFT — visual, listening, factual, permission and platform review required','automatic_checks':['full decode','dimensions','duration','audio windows','anchor in transcript','contact sheet'],'not_automatic':['meaning, truth and context','rights and permission','human visual/audio review','social-media publication']}
    report['voice_profile']=VOICE_PROFILE['profile_id']
    report['voice_id']=None # A prerecorded file does not reveal or prove the model or speaker identity.
    report['voice_processing_filter']=VOICE_FILTER
    report['voice_identity_caveat']='Pre-recorded clip identity is not automatically verified' if s['tts']['provider']=='pre_recorded' else 'Provider voice may change or become unavailable; review by ear'
    report['brand_release']=json.loads((ROOT/'assets/brand/brand_manifest.json').read_text(encoding='utf-8')).get('release_id','legacy')
    report['speech_tempo_review']=[e['id'] for e in events if e['tempo']>1.25]
    report['creative_plan']=plan
    report['framing']=frame_analysis
    report['automatic_checks'].extend(['creative plan validation','sampled face-aware framing warnings'])
    report['not_automatic'].append('all-frame face, caption and logo occlusion detection')
    (OUTPUT/'source_analysis.json').write_text(json.dumps(frame_analysis,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUTPUT/'qa_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copy2(local_path(s['transcript_file']),OUTPUT/'transcript_words.json')
    (OUTPUT/'used_spec.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--spec',default='spec.json');ap.add_argument('--source',help='Local source override for testing; not embedded into the repository');ap.add_argument('--validate-only',action='store_true');a=ap.parse_args()
    profile=brand_lock.verify();print('Golden brand assets verified:',profile,flush=True)
    s=load_spec(a.spec);print('Spec and anchor checks passed',flush=True)
    if a.validate_only:return
    if s['tts']['provider']=='elevenlabs' and (not os.environ.get('ELEVENLABS_API_KEY','').strip() or not os.environ.get('ELEVENLABS_VOICE_ID','').strip()):
        fail('ElevenLabs voice is not configured; securely add ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID before production')
    from PIL import features
    if not features.check_feature('raqm'):fail('Pillow must include RAQM for proper Arabic shaping')
    for p in (WORK,OUTPUT):
        if p.exists():shutil.rmtree(p)
        p.mkdir(parents=True)
    plan=creative_plan.validate(s)
    print('Creative layout:',plan['mode'],'selection:',plan['selection'],flush=True)
    source=prepare_source(s,a.source)
    frame_analysis=framing.analyze(source,s,plan)
    print('Framing:',frame_analysis['crop_reason'],'cards:',frame_analysis['card_position'],flush=True)
    for warning in frame_analysis['warnings']:print('FRAMING WARNING:',warning,flush=True)
    events,source_audio_status,sfx_events=generate_mix(s,source)
    adaptive_motion.picture(WORK,source,s,plan,frame_analysis)
    video=OUTPUT/(s['project_id']+'_Motion_V2.mp4')
    run([FF,'-y','-hide_banner','-loglevel','error','-i',WORK/'picture.mp4','-i',WORK/'mix_master.wav','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar',str(SR),'-t',str(DURATION),'-movflags','+faststart',video])
    qa(s,video,events,source_audio_status,sfx_events,plan,frame_analysis)
    print('\nDELIVERABLE:',video,flush=True)

if __name__=='__main__':
    try:main()
    except Exception as e:
        print(f'ERROR: {e}',file=sys.stderr);sys.exit(1)
