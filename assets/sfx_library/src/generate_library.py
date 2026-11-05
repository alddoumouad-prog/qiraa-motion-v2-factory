#!/usr/bin/env python3
"""Qiraa Tactile UI SFX — deterministic original procedural sound library.
No recordings or third-party samples are used. Requires numpy and FFmpeg for MP3.
"""
from __future__ import annotations
import csv, hashlib, json, math, os, subprocess, wave
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SR=48000
PEAK_DB=-15.0
VERSION='1.0.0'

CATEGORIES=[
 ('TAP','Taps','لمسات', ['FeatherTap','SoftTap','CrispTap','FirmTap','VelvetTap','StudioTap','MicroTap','RoundedTap','SnapTap','MutedTap']),
 ('CLK','Clicks','نقرات', ['MechanicalClick','CeramicClick','CrispClick','SoftClick','DeepClick','TinyClick','DoubleClick','SwitchClick','TickClick','PulseClick']),
 ('PRS','Presses','ضغطات', ['SoftPress','DeepPress','ThockPress','ButtonPress','PressRelease','HeavyPress','CompactPress','RoundedPress','SubtlePress','LowPress']),
 ('TGL','Toggles','مفاتيح', ['ToggleOn','ToggleOff','SwitchOn','SwitchOff','ToggleSoft','ToggleCrisp','ToggleDeep','SlideToggle','MicroToggle','ConfirmToggle']),
 ('TXT','Text_Reveal','كشف النصوص', ['TextReveal','LineReveal','WordTick','NumberTick','TypePulse','CaptionIn','CaptionOut','TitleSettle','SubtitleIn','KineticTick']),
 ('CRD','Cards','البطاقات', ['CardIn','CardOut','CardPop','CardSettle','BentoIn','BentoOut','CardLift','CardDrop','GlassCard','CardSequence']),
 ('SWP','Swipes','سحب وحركة', ['SoftSwipe','DeepSwipe','LowWhoosh','LeftSwipe','RightSwipe','UpSwipe','DownSwipe','MacroIn','MacroOut','AirSettle']),
 ('NTF','Notifications','التنبيهات', ['SoftNotify','MessagePing','SubtleBell','NotificationPop','GentleAlert','UIBeacon','QuietNotice','BadgePop','PingRounded','NotifyGlass']),
 ('SUC','Success','النجاح والإتمام', ['SuccessSoft','Complete','Confirmed','Done','SuccessTick','SuccessChime','UploadDone','Saved','Ready','Positive']),
 ('ALT','Alerts','التنبيه والتراجع', ['ErrorSoft','WarningSoft','MutedError','BackOut','Cancel','Denied','Retry','Offline','Caution','Negative']),
 ('KEY','Keyboard','لوحة المفاتيح', ['KeyTap','KeySoft','KeyThock','KeyClick','Spacebar','EnterKey','Backspace','KeySequence','TypingBurst','NumpadTick']),
 ('TRN','Transitions','الانتقالات', ['SceneIn','SceneOut','DeepMacro','SoftCut','RevealUp','RevealDown','FocusIn','FocusOut','LoopSettle','LogoClick']),
]

USES={
 'TAP':'Buttons, small UI touches, timeline markers','CLK':'Mechanical UI clicks and tactile feedback','PRS':'Press/release actions and weighted buttons','TGL':'On/off switches and state changes','TXT':'Headline, subtitle, word and number reveals','CRD':'Bento cards, panels, lifts and settling motion','SWP':'Low-passed swipes and camera movement under 500 Hz','NTF':'Subtle messages, badges and notifications','SUC':'Save, complete, confirmation and positive states','ALT':'Muted errors, cancel, retry and warning states','KEY':'Keyboard, typing and editing sequences','TRN':'Scene changes, macro transitions and logo outro'
}


def env_exp(t,decay,attack=4000):return (1-np.exp(-t*attack))*np.exp(-t*decay)
def sine(f,t,phase=0):return np.sin(2*np.pi*f*t+phase)
def norm_noise(rng,n):return rng.normal(0,1,n)
def lowpass(x,cut):
 n=len(x);spec=np.fft.rfft(x);freq=np.fft.rfftfreq(n,1/SR);spec[freq>cut]=0;return np.fft.irfft(spec,n)
def highpass(x,cut):
 n=len(x);spec=np.fft.rfft(x);freq=np.fft.rfftfreq(n,1/SR);spec[freq<cut]=0;return np.fft.irfft(spec,n)
def place(dst,sig,at,gain=1):
 i=round(at*SR);n=min(len(sig),len(dst)-i)
 if n>0:dst[i:i+n]+=sig[:n]*gain

def click(rng,dur=.16,f=1450,decay=48,noise=.28,brightness=1.0):
 t=np.arange(round(dur*SR))/SR;phase=rng.uniform(0,np.pi)
 sig=.8*sine(f,t,phase)*env_exp(t,decay)+.32*sine(f*2.17,t)*env_exp(t,decay*1.7)
 nz=highpass(norm_noise(rng,len(t)),700*brightness)*env_exp(t,decay*2.2,9000)
 return sig+nz*noise

def thock(rng,dur=.24,f=180,decay=28,top=.25):
 t=np.arange(round(dur*SR))/SR
 sig=sine(f,t)*env_exp(t,decay,2500)+.45*sine(f*1.52,t)*env_exp(t,decay*1.35)
 sig+=lowpass(norm_noise(rng,len(t)),1300)*env_exp(t,decay*2.4)*.17
 place(sig,click(rng,min(.1,dur),f*5.5,70,top),0,.35)
 return sig

def air(rng,dur=.55,cut=500,reverse=False):
 t=np.arange(round(dur*SR))/SR;x=t/dur
 noise=lowpass(norm_noise(rng,len(t)),cut)
 envelope=np.sin(np.pi*x)**1.8
 if reverse:envelope=envelope[::-1]
 tone=sine(75+35*x,t)*np.sin(np.pi*x)**2*.13
 return noise*envelope*.65+tone

def bell(rng,dur=.5,f=880,decay=10):
 t=np.arange(round(dur*SR))/SR
 return (sine(f,t)+.35*sine(f*2.01,t)+.16*sine(f*3.98,t))*env_exp(t,decay,1800)

def finish(x,channels=1,pan=0.0):
 x=np.asarray(x,dtype=float);x-=np.mean(x)
 # Micro fade only removes boundary DC; the tactile attack remains intact.
 fade=min(24,len(x)//20);end=min(240,len(x)//4)
 if fade>1:x[:fade]*=np.linspace(0,1,fade)
 if end>1:x[-end:]*=np.linspace(1,0,end)
 if channels==2:
  if pan<0:x=np.column_stack([x*(1+abs(pan)*.35),x*(1-abs(pan)*.35)])
  else:x=np.column_stack([x*(1-pan*.35),x*(1+pan*.35)])
 peak=np.max(np.abs(x)) or 1;x=x/peak*(10**(PEAK_DB/20))
 return x

def write_wav24(path,x):
 path.parent.mkdir(parents=True,exist_ok=True);data=np.clip(x,-.999999,.999999)
 pcm=(data*8388607).astype('<i4').reshape(-1);packed=pcm.view(np.uint8).reshape(-1,4)[:,:3].tobytes()
 with wave.open(str(path),'wb') as w:w.setnchannels(1 if x.ndim==1 else x.shape[1]);w.setsampwidth(3);w.setframerate(SR);w.writeframes(packed)

def synthesize(code,index,rng):
 v=index-1
 if code=='TAP':
  x=click(rng,.10+v*.008,1050+v*155,58+v*3,.14+v*.025,1+v*.08);return finish(x)
 if code=='CLK':
  if index in (7,10):
   x=np.zeros(round(.32*SR));place(x,click(rng,.12,1200+v*130,65,.32),.0);place(x,click(rng,.1,1700+v*90,72,.2),.075);return finish(x)
  return finish(click(rng,.12+v*.009,1300+v*170,60+v*2,.26+v*.025,1.2))
 if code=='PRS':
  x=thock(rng,.20+v*.012,125+v*24,24+v*1.6,.18+v*.025)
  if index==5:place(x,click(rng,.1,1800,70,.16),.13)
  return finish(x)
 if code=='TGL':
  x=np.zeros(round(.30*SR));ratio=.82 if index%2==0 else 1.22;f=980+v*105
  place(x,click(rng,.11,f,68,.2),.0);place(x,click(rng,.12,f*ratio,62,.24),.085+v*.003);return finish(x)
 if code=='TXT':
  x=np.zeros(round((.22+.04*(index%4))*SR));count=1 if index in (1,3,4,10) else 2+(index%3)
  for j in range(count):place(x,click(rng,.09,1650+v*100+j*135,76,.12),j*.045)
  return finish(x)
 if code=='CRD':
  dur=.32+v*.012;x=air(rng,dur,min(490,380+12*v),reverse=index%2==0);place(x,thock(rng,.18,160+v*20,32,.1),dur*.35,.65);return finish(x,2,(-1 if index%2 else 1)*.25)
 if code=='SWP':
  return finish(air(rng,.45+v*.035,320+18*v,reverse=index in (2,9)),2,-.65+v*.14)
 if code=='NTF':
  x=np.zeros(round(.65*SR));f=720+v*48;place(x,bell(rng,.48,f,12+v*.3),0)
  if index in (2,4,6,8):place(x,bell(rng,.42,f*1.25,14),.12,.55)
  return finish(x)
 if code=='SUC':
  x=np.zeros(round(.85*SR));base=520+v*18;steps=[1,1.25,1.5] if index%2 else [1,1.333]
  for j,ratio in enumerate(steps):place(x,bell(rng,.58,base*ratio,10+v*.3),j*.105,.7-j*.1)
  return finish(x)
 if code=='ALT':
  dur=.38+v*.018;t=np.arange(round(dur*SR))/SR;f=145+v*13
  x=(sine(f,t)+.45*sine(f*1.06,t))*env_exp(t,14,900)
  x*=.55+.45*np.sin(2*np.pi*(7+v*.25)*t)**2;x+=lowpass(norm_noise(rng,len(t)),450)*.08*env_exp(t,24)
  return finish(x)
 if code=='KEY':
  if index>=8:
   x=np.zeros(round(.65*SR));count=3 if index==8 else 5
   for j in range(count):place(x,thock(rng,.12,230+rng.uniform(-35,35),44,.28),j*(.085 if index==8 else .055),.6)
   return finish(x)
  return finish(thock(rng,.13+v*.008,190+v*22,38+v*2,.32+v*.03))
 if code=='TRN':
  dur=.48+v*.045;x=air(rng,dur,min(490,380+10*v),reverse=index in (2,4,6,8));place(x,thock(rng,.22,100+v*12,24,.1),dur*.55,.55)
  if index==10:place(x,click(rng,.16,1200,55,.18),dur*.6,.8)
  return finish(x,2,.35-v*.07)
 raise ValueError(code)


def main():
 audio=ROOT/'audio';audio.mkdir(exist_ok=True);items=[];hashes=[]
 for code,category,arabic,names in CATEGORIES:
  for index,name in enumerate(names,1):
   ident=f'QT_{code}_{index:03d}';filename=f'{ident}_{name}';seed=int(hashlib.sha256(ident.encode()).hexdigest()[:16],16);rng=np.random.default_rng(seed)
   x=synthesize(code,index,rng);channels=1 if x.ndim==1 else x.shape[1]
   wav=audio/category/(filename+'.wav');mp3=audio/category/(filename+'.mp3');write_wav24(wav,x)
   subprocess.run([os.environ.get('FFMPEG') or 'ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(wav),'-codec:a','libmp3lame','-b:a','192k',str(mp3)],check=True)
   duration=len(x)/SR;peak=20*np.log10(np.max(np.abs(x))+1e-12);centroid=float(np.mean(np.abs(np.diff(x)))*SR/1000)
   item={'id':ident,'title':name,'category':category,'category_ar':arabic,'index':index,'wav':str(wav.relative_to(ROOT)),'mp3':str(mp3.relative_to(ROOT)),'duration_ms':round(duration*1000),'sample_rate':SR,'bit_depth':24,'channels':channels,'peak_dbfs':round(float(peak),2),'energy':round(float(np.sqrt(np.mean(x*x))),5),'suggested_use':USES[code],'license':'MIT','generator_seed':seed}
   items.append(item)
   for p in (wav,mp3):hashes.append((hashlib.sha256(p.read_bytes()).hexdigest(),str(p.relative_to(ROOT))))
   print(ident,name,round(duration*1000),'ms',channels,'ch',flush=True)
 (ROOT/'library.json').write_text(json.dumps({'name':'Qiraa Tactile UI SFX','version':VERSION,'count':len(items),'sample_rate':SR,'bit_depth':24,'peak_dbfs':PEAK_DB,'items':items},ensure_ascii=False,indent=2))
 with (ROOT/'library.csv').open('w',newline='',encoding='utf-8-sig') as f:
  fields=['id','title','category','category_ar','duration_ms','sample_rate','bit_depth','channels','peak_dbfs','wav','mp3','suggested_use','license'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for item in items:w.writerow({k:item[k] for k in fields})
 (ROOT/'manifest.sha256').write_text(''.join(f'{h}  {p}\n' for h,p in hashes))
 (ROOT/'library.js').write_text('window.QIRAA_LIBRARY = '+json.dumps(items,ensure_ascii=False)+';\n')
 # Short original demo: one sound per family, separated by silence.
 demo=np.zeros(round(12*1.05*SR))
 for j,item in enumerate(items[::10]):
  ident=item['id'];rng=np.random.default_rng(item['generator_seed']);code=ident.split('_')[1];x=synthesize(code,item['index'],rng)
  if x.ndim==2:x=x.mean(1)
  place(demo,x,j*1.05,.85)
 write_wav24(ROOT/'demo/Qiraa_Tactile_Demo.wav',demo)
 subprocess.run([os.environ.get('FFMPEG') or 'ffmpeg','-y','-hide_banner','-loglevel','error','-i',str(ROOT/'demo/Qiraa_Tactile_Demo.wav'),'-codec:a','libmp3lame','-b:a','192k',str(ROOT/'demo/Qiraa_Tactile_Demo.mp3')],check=True)
 print('DONE',len(items),'original sounds')

if __name__=='__main__':main()
