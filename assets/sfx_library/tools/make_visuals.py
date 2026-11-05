#!/usr/bin/env python3
from pathlib import Path
import json,wave
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets';OUT.mkdir(exist_ok=True)
BLUE=(0,113,227);BG=(5,5,7);TEXT=(245,245,247);MUTED=(134,134,139)
def samples(path):
 with wave.open(str(path),'rb') as w:raw=w.readframes(w.getnframes());ch=w.getnchannels()
 b=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3).astype(np.int32);v=b[:,0]|(b[:,1]<<8)|(b[:,2]<<16);v=np.where(v&0x800000,v-(1<<24),v).reshape(-1,ch)
 return v.mean(1)/8388608
def font(size,bold=False):
 for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
  if Path(p).exists():return ImageFont.truetype(p,size)
 return ImageFont.load_default()
# Social preview
im=Image.new('RGB',(1280,640),BG);d=ImageDraw.Draw(im);d.ellipse((850,-220,1450,380),fill=(0,45,87));d.ellipse((990,-120,1370,260),fill=(0,75,140));d.text((72,66),'QIRAA THANIYA',font=font(22,True),fill=BLUE);d.text((68,132),'Tactile UI SFX',font=font(76,True),fill=TEXT);d.text((72,236),'120 original procedural sounds',font=font(30),fill=MUTED);d.text((72,302),'48 kHz / 24-bit WAV  •  MP3  •  MIT',font=font(23),fill=(190,190,196))
rng=np.random.default_rng(120);x=np.linspace(72,1200,720);wave_y=np.sin(np.linspace(0,45,720))*np.exp(-np.linspace(0,3,720));wave_y+=rng.normal(0,.04,720)
for j in range(len(x)-1):d.line((x[j],480+wave_y[j]*90,x[j+1],480+wave_y[j+1]*90),fill=BLUE,width=3)
d.text((72,566),'TAPS  •  CLICKS  •  CARDS  •  TEXT  •  SWIPES  •  TRANSITIONS',font=font(17,True),fill=MUTED);im.save(OUT/'social-preview.png')
# Twelve representative waveforms
items=json.loads((ROOT/'library.json').read_text())['items'][::10];im=Image.new('RGB',(1600,1000),(12,12,14));d=ImageDraw.Draw(im);d.text((50,28),'Qiraa Tactile UI SFX — Representative Waveforms',font=font(32,True),fill=TEXT)
for i,item in enumerate(items):
 x0=50+(i%3)*520;y0=100+(i//3)*220;s=samples(ROOT/item['wav']);n=460;step=max(1,len(s)//n);vals=[np.max(np.abs(s[j:j+step])) for j in range(0,len(s),step)][:n]
 d.rounded_rectangle((x0,y0,x0+480,y0+180),radius=18,fill=(29,29,31));d.text((x0+18,y0+14),item['title'],font=font(20,True),fill=TEXT);d.text((x0+18,y0+43),f"{item['id']}  |  {item['duration_ms']} ms",font=font(12),fill=MUTED);mid=y0+120
 for j,v in enumerate(vals):d.line((x0+12+j,mid-v*42,x0+12+j,mid+v*42),fill=BLUE)
im.save(OUT/'waveform-overview.jpg',quality=94)
print('Visual assets created')
