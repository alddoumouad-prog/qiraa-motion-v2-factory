#!/usr/bin/env python3
"""Restored Qiraa Thaniya Motion V2 — vertical red/ivory/green news template."""
from pathlib import Path
import argparse, os, subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

W,H,FPS=1080,1920,30
SOURCE_END=45.633333
DURATION=50.633333
FRAMES=1519
RED='#E60012'; IVORY='#F4F0E6'; GREEN='#0D211E'; GREEN_2='#071714'
ROOT=Path(__file__).resolve().parent

def rgb(h):h=h.lstrip('#');return tuple(int(h[i:i+2],16) for i in (0,2,4))
def rgba(h,a=255):return (*rgb(h),a)
def clamp(x):return max(0,min(1,x))
def ease(x):x=clamp(x);return 1-(1-x)**3
def ar(s):return any('\u0600'<=c<='\u06ff' for c in s)

class Source:
 def __init__(self,path):
  self.path=str(path);self.cap=cv2.VideoCapture(path);self.fps=self.cap.get(cv2.CAP_PROP_FPS) or 29.978;self.count=int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT));self.idx=-1;self.frame=None;self.pil=None;self.key=None
 def get(self,t):
  target=max(0,min(round(t*self.fps),self.count-1))
  if self.frame is None or target<self.idx:
   self.cap.release();self.cap=cv2.VideoCapture(self.path);self.idx=-1;self.frame=None
  while self.idx<target:
   ok,fr=self.cap.read()
   if not ok:break
   self.idx+=1;self.frame=fr
  if self.key!=self.idx:
   self.pil=Image.fromarray(cv2.cvtColor(self.frame,cv2.COLOR_BGR2RGB));self.key=self.idx
  return self.pil
 def close(self):self.cap.release()

class Classic:
 def __init__(self,source,content,brand):
  self.src=Source(source);self.c=content;self.brand=Path(brand);self.cairo=str(self.brand/'Cairo.ttf');self.inter=str(self.brand/'Inter.ttf')
  self.icon=Image.open(self.brand/'logo_icon.png').convert('RGBA');self.wm=Image.open(self.brand/'logo_wordmark.png').convert('RGBA');self.cache={};self.tiles={};self.fit={}
  self.opening=self.make_opening();self.brand_layer=self.make_brand();self.meta=self.make_meta();self.outro=self.make_outro()
 def font(self,size,latin=False):return ImageFont.truetype(self.inter if latin else self.cairo,size)
 def tile(self,text,size,color,weight='Bold',latin=False):
  k=(text,size,color,weight,latin)
  if k in self.tiles:return self.tiles[k]
  f=self.font(size,latin)
  try:f.set_variation_by_name(weight.encode())
  except:pass
  tmp=Image.new('RGBA',(max(700,len(text)*size*2),size*3),(0,0,0,0));d=ImageDraw.Draw(tmp)
  d.text((30,15),text,font=f,fill=rgba(color),direction='rtl' if ar(text) else 'ltr',language='ar' if ar(text) else 'en')
  box=tmp.getbbox();im=tmp.crop((max(0,box[0]-5),max(0,box[1]-5),min(tmp.width,box[2]+5),min(tmp.height,box[3]+5)))
  self.tiles[k]=im;return im
 def paste(self,base,im,x,y,opacity=1,anchor='left'):
  if opacity<=0:return
  if opacity<.999:
   im=im.copy();im.putalpha(im.getchannel('A').point(lambda v:round(v*clamp(opacity))))
  if anchor=='center':x-=im.width/2
  elif anchor=='right':x-=im.width
  base.paste(im,(round(x),round(y)),im)
 def fitted(self,t):
  src=self.src.get(t);k=self.src.key
  if k not in self.fit:
   if len(self.fit)>4:self.fit.clear()
   self.fit[k]=ImageOps.fit(src,(W,H),Image.Resampling.LANCZOS).convert('RGBA')
  return self.fit[k].copy()
 def make_opening(self):
  cap=cv2.VideoCapture(str(self.src.path));cap.set(cv2.CAP_PROP_POS_MSEC,3000);ok,fr=cap.read();cap.release()
  src=Image.fromarray(cv2.cvtColor(fr,cv2.COLOR_BGR2RGB));bg=ImageOps.fit(src,(W,H),Image.Resampling.LANCZOS).convert('RGBA')
  shade=Image.new('RGBA',(W,H),rgba(GREEN,215));bg=Image.alpha_composite(bg,shade)
  rings=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(rings)
  for r,a in [(120,170),(220,120),(330,85),(450,50)]:d.ellipse((540-r,1090-r,540+r,1090+r),outline=rgba(RED,a),width=4)
  bg=Image.alpha_composite(bg,rings)
  icon=self.icon.resize((145,145),Image.Resampling.LANCZOS);bg.paste(icon,(468,1018),icon)
  wm=self.wm.resize((340,137),Image.Resampling.LANCZOS);bg.paste(wm,(370,1190),wm)
  return bg
 def make_brand(self):
  im=Image.new('RGBA',(W,H),(0,0,0,0));icon=self.icon.resize((108,108),Image.Resampling.LANCZOS);im.paste(icon,(892,120),icon)
  wm=self.wm.resize((320,129),Image.Resampling.LANCZOS);im.paste(wm,(540,110),wm);return im
 def make_meta(self):
  im=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(im)
  d.ellipse((70,330,88,348),fill=rgba(RED));d.ellipse((76,336,82,342),fill=rgba(IVORY))
  self.paste(im,self.tile(self.c['location'],32,IVORY,'Medium'),105,315)
  d.rounded_rectangle((70,382,90,402),radius=3,outline=rgba(IVORY),width=2);d.line((70,389,90,389),fill=rgba(RED),width=3)
  self.paste(im,self.tile(self.c['date'],32,IVORY,'Medium',True),105,370)
  credit=self.tile('SOURCE: X / @ZelenskyyUa  •  UKRAINIAN EMERGENCY SERVICE',24,IVORY,'Regular',True)
  credit=credit.rotate(90,expand=True);im.paste(credit,(36,580),credit)
  return im
 def make_outro(self):
  im=Image.new('RGBA',(W,H),rgba(GREEN_2));d=ImageDraw.Draw(im)
  for r,a in [(180,120),(300,85),(440,55),(600,30)]:d.ellipse((540-r,570-r,540+r,570+r),outline=rgba(RED,a),width=4)
  icon=self.icon.resize((180,180),Image.Resampling.LANCZOS);im.paste(icon,(450,390),icon)
  wm=self.wm.resize((400,161),Image.Resampling.LANCZOS);im.paste(wm,(340,640),wm)
  self.paste(im,self.tile('Instagram  •  TikTok  •  X',30,IVORY,'Medium',True),540,1640,1,'center')
  self.paste(im,self.tile('المصدر: X / الرئاسة الأوكرانية / خدمة الطوارئ',26,IVORY,'Regular'),540,1740,.75,'center')
  return im
 def pill(self,text,fill,text_color):
  im=Image.new('RGBA',(960,140),(0,0,0,0));d=ImageDraw.Draw(im);d.rounded_rectangle((0,0,959,139),radius=70,fill=rgba(fill))
  self.paste(im,self.tile(text,44,text_color,'Bold'),480,35,1,'center');return im
 def cta(self,text,index):
  im=Image.new('RGBA',(600,140),(0,0,0,0));d=ImageDraw.Draw(im);d.rounded_rectangle((0,0,599,139),radius=36,fill=rgba(IVORY))
  d.ellipse((36,31,114,109),fill=rgba(RED));self.paste(im,self.tile(f'{index:02d}',30,IVORY,'Bold',True),75,48,1,'center')
  self.paste(im,self.tile(text,54,GREEN,'Bold'),340,31,1,'center');return im
 def render(self,t):
  if t>=SOURCE_END:
   p=ease((t-SOURCE_END)/.4);base=self.outro.copy()
   for i,(txt,start) in enumerate([('تفاعل',46.1),('عبّر',46.8),('شارك',47.5)]):
    q=ease((t-start)/.45)
    if q>0:self.paste(base,self.cta(txt,i+1),240,880+i*220+30*(1-q),q,'left')
   return base.convert('RGB')
  current=self.fitted(t)
  if t<.65:
   op=1 if t<.55 else 1-(t-.55)/.1;base=Image.blend(current,self.opening,clamp(op))
   for i,start in enumerate([.05,.17,.29]):
    p=ease((t-start)/.2);txt=self.c['headline_lines'][i];fill=IVORY if i==0 else RED;tc=GREEN if i==0 else IVORY
    if p>0:self.paste(base,self.pill(txt,fill,tc),60,540+i*160+60*(1-p),p*clamp(op))
  else:base=current
  brand_op=ease((t-.65)/.35);self.paste(base,self.brand_layer,0,0,brand_op)
  meta_op=ease((t-1.35)/.35)
  if t>8.9:meta_op*=1-clamp((t-8.9)/.45)
  self.paste(base,self.meta,0,0,meta_op)
  if .65<=t<9.6:
   cp=ease((t-.65)/.35);exitp=clamp((t-9.05)/.55) if t>9.05 else 0;card_op=cp*(1-exitp);dy=35*(1-cp)+30*exitp
   card=Image.new('RGBA',(880,380),(0,0,0,0));d=ImageDraw.Draw(card);d.rounded_rectangle((0,0,879,379),radius=42,fill=rgba(RED))
   self.paste(base,card,100,980+dy,card_op)
   for i,start in enumerate([.82,1.0,1.18]):
    lp=ease((t-start)/.3);fade=1-clamp((t-8.9)/.45) if t>8.9 else 1
    if lp>0 and fade>0:
     line=self.tile(self.c['headline_lines'][i],58,IVORY,'Bold')
     self.paste(base,line,540,1015+i*105+dy+20*(1-lp),lp*fade,'center')
  return base.convert('RGB')

def ffmpeg():
 import imageio_ffmpeg
 return os.environ.get('FFMPEG') or imageio_ffmpeg.get_ffmpeg_exe()

def render(source,content,outdir,stills=False):
 outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True);r=Classic(source,content,ROOT/'brand')
 if stills:
  for t in [.15,.5,1.35,3,6,9.3,9.65,46.1,47.8,50.2]:r.render(t).save(outdir/f'frame_{t:05.2f}.jpg',quality=94)
  r.src.close();return
 ff=ffmpeg();picture=outdir/'picture.mp4';final=outdir/'Qiraa_Thaniya_Motion_V2.mp4'
 cmd=[ff,'-y','-hide_banner','-loglevel','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(picture)]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 try:
  for n in range(FRAMES):
   proc.stdin.write(r.render(n/FPS).tobytes())
   if n%150==0:print(f'Render {n}/{FRAMES}',flush=True)
 finally:proc.stdin.close()
 if proc.wait():raise RuntimeError('Video encoding failed')
 r.render(3).save(outdir/'Qiraa_Thaniya_Motion_V2_Cover.jpg',quality=95);r.src.close()
 fc=f'[1:a]atrim=0:{SOURCE_END},aresample=48000,apad=whole_dur={DURATION}[a]'
 cmd=[ff,'-y','-hide_banner','-loglevel','warning','-i',str(picture),'-i',str(source),'-filter_complex',fc,'-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(DURATION),'-movflags','+faststart',str(final)]
 subprocess.run(cmd,check=True);print(final)

if __name__=='__main__':
 import json
 ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--content',required=True);ap.add_argument('--outdir',required=True);ap.add_argument('--stills',action='store_true');a=ap.parse_args()
 render(a.source,json.loads(Path(a.content).read_text()),a.outdir,a.stills)
