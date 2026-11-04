#!/usr/bin/env python3
"""Qiraa Thaniya Motion V2 — fast red/ivory/green space-voting sample."""
from pathlib import Path
import argparse, importlib.util, os, subprocess
from PIL import Image, ImageDraw, ImageFilter

ROOT=Path(__file__).resolve().parent.parent
SPEC=importlib.util.spec_from_file_location('motion_base',ROOT/'factory/classic_renderer.py')
base=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(base)
W,H,FPS=base.W,base.H,30
DURATION=28.0; SOURCE_END=23.5; FRAMES=round(DURATION*FPS)
RED=base.RED;IVORY=base.IVORY;GREEN=base.GREEN;GREEN_2=base.GREEN_2
ORANGE='#FF9F0A'

def ease01(t,start,dur):return base.ease((t-start)/dur)


class MotionSpace(base.Classic):
    def tile_fit(self,text,size,color,weight='Bold',latin=False,max_width=760):
        tile=self.tile(text,size,color,weight,latin)
        while tile.width>max_width and size>22:
            size-=2;tile=self.tile(text,size,color,weight,latin)
        return tile

    def pill(self,text,fill,text_color):
        im=Image.new('RGBA',(960,140),(0,0,0,0));d=ImageDraw.Draw(im)
        d.rounded_rectangle((0,0,959,139),radius=70,fill=base.rgba(fill))
        tile=self.tile_fit(text,44,text_color,max_width=860)
        self.paste(im,tile,480,(140-tile.height)//2,1,'center');return im

    def make_meta(self):
        im=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(im)
        # Right-side metadata avoids covering the astronaut's face.
        d.rounded_rectangle((610,300,1010,438),radius=28,fill=base.rgba(GREEN,205))
        d.ellipse((970,326,988,344),fill=base.rgba(RED));d.ellipse((976,332,982,338),fill=base.rgba(IVORY))
        self.paste(im,self.tile_fit(self.c['location'],30,IVORY,'Medium',max_width=320),950,315,1,'right')
        d.rounded_rectangle((970,382,990,402),radius=3,outline=base.rgba(IVORY),width=2);d.line((970,389,990,389),fill=base.rgba(RED),width=3)
        self.paste(im,self.tile(self.c['date'],30,IVORY,'Medium',True),950,370,1,'right')
        return im

    def make_credit(self):
        im=Image.new('RGBA',(W,H),(0,0,0,0))
        credit=self.tile(self.c['source_credit'],24,IVORY,'Regular',not base.ar(self.c['source_credit'])).rotate(90,expand=True)
        im.paste(credit,(36,620),credit)
        return im

    def make_outro(self):
        im=Image.new('RGBA',(W,H),base.rgba(GREEN_2));d=ImageDraw.Draw(im)
        for r,a in [(180,120),(300,85),(440,55),(600,30)]:d.ellipse((540-r,570-r,540+r,570+r),outline=base.rgba(RED,a),width=4)
        icon=self.icon.resize((180,180),Image.Resampling.LANCZOS);im.paste(icon,(450,390),icon)
        wm=self.wm.resize((400,161),Image.Resampling.LANCZOS);im.paste(wm,(340,640),wm)
        self.paste(im,self.tile('Instagram  •  TikTok  •  X',30,IVORY,'Medium',True),540,1640,1,'center')
        self.paste(im,self.tile_fit('المصدر: '+self.c['source_credit'],27,IVORY,'Regular',max_width=900),540,1740,.8,'center')
        return im

    def info_card(self,kicker,value,sub='',fill=RED,text_color=IVORY):
        key=('info',kicker,value,sub,fill,text_color)
        if key in self.cache:return self.cache[key]
        im=Image.new('RGBA',(880,260),(0,0,0,0));d=ImageDraw.Draw(im)
        d.rounded_rectangle((0,0,879,259),radius=42,fill=base.rgba(fill))
        d.rounded_rectangle((34,30,48,110),radius=7,fill=base.rgba(text_color))
        self.paste(im,self.tile_fit(kicker,28,text_color,'Medium',max_width=750),840,28,1,'right')
        # Step down only when necessary; never truncate the fact.
        size=62;tile=self.tile(value,size,text_color,'Bold')
        while tile.width>760 and size>40:
            size-=2;tile=self.tile(value,size,text_color,'Bold')
        self.paste(im,tile,840,83,1,'right')
        if sub:self.paste(im,self.tile_fit(sub,28,text_color,'Regular',max_width=750),840,190,.82,'right')
        self.cache[key]=im;return im

    def micro_layer(self,text):
        key=('micro',text)
        if key in self.cache:return self.cache[key]
        w,h=720,124;im=Image.new('RGBA',(w,h),(0,0,0,0));d=ImageDraw.Draw(im)
        d.rounded_rectangle((0,0,w-1,h-1),radius=62,fill=(0,0,0,240),outline=base.rgba(IVORY,55),width=2)
        d.ellipse((w-86,38,w-38,86),fill=base.rgba(ORANGE))
        d.rounded_rectangle((w-68,48,w-56,68),radius=6,fill=(0,0,0,255));d.arc((w-74,53,w-50,77),0,180,fill=(0,0,0,255),width=3);d.line((w-62,75,w-62,81),fill=(0,0,0,255),width=3)
        label=self.tile_fit(text,42,IVORY,'Medium',max_width=570)
        im.paste(label,(w-112-label.width,(h-label.height)//2-2),label)
        self.cache[key]=im;return im

    def place_card(self,im,card,t,start,end,y=1370):
        enter=ease01(t,start,.32);exitp=base.clamp((t-(end-.35))/.35) if t>end-.35 else 0
        op=enter*(1-exitp)
        if op>0:self.paste(im,card,100,y+35*(1-enter)+30*exitp,op)

    def finish(self,im,t):
        for micro in self.c['micro']:
            start,text=micro['start'],micro['text']
            local=t-start
            if 0<=local<2.0:
                p=min(ease01(local,0,.16),ease01(2.0-local,0,.16))
                layer=self.micro_layer(text)
                self.paste(im,layer,180,1540+20*(1-p),p)
        return im.convert('RGB')

    def render_outro(self,t):
        im=self.outro.copy()
        for i,(txt,start) in enumerate([('تفاعل',23.85),('عبّر',24.50),('شارك',25.15)]):
            q=ease01(t,start,.38)
            if q>0:self.paste(im,self.cta(txt,i+1),240,880+i*220+30*(1-q),q)
        return im.convert('RGB')

    def render(self,t):
        if t>=SOURCE_END:return self.render_outro(t)
        current=self.fitted(t)
        if t<.65:
            op=1 if t<.55 else 1-(t-.55)/.1;im=Image.blend(current,self.opening,base.clamp(op))
            for i,start in enumerate([.05,.17,.29]):
                p=ease01(t,start,.2);txt=self.c['headline_lines'][i];fill=IVORY if i==0 else RED;tc=GREEN if i==0 else IVORY
                if p>0:self.paste(im,self.pill(txt,fill,tc),60,540+i*160+60*(1-p),p*base.clamp(op))
        else:im=current
        self.paste(im,self.brand_layer,0,0,ease01(t,.65,.30))
        meta_op=ease01(t,1.0,.30)
        if t>4.7:meta_op*=1-base.clamp((t-4.7)/.35)
        self.paste(im,self.meta,0,0,meta_op)
        self.paste(im,self.credit,0,0,.78*ease01(t,1.15,.35))
        if .65<=t<5.22:
            cp=ease01(t,.65,.30);exitp=base.clamp((t-4.72)/.50) if t>4.72 else 0;op=cp*(1-exitp);dy=35*(1-cp)+30*exitp
            card=Image.new('RGBA',(880,380),(0,0,0,0));d=ImageDraw.Draw(card);d.rounded_rectangle((0,0,879,379),radius=42,fill=base.rgba(RED))
            self.paste(im,card,100,980+dy,op)
            for i,start in enumerate([.82,1.0,1.18]):
                lp=ease01(t,start,.27);fade=1-base.clamp((t-4.70)/.40) if t>4.70 else 1
                if lp>0 and fade>0:self.paste(im,self.tile_fit(self.c['headline_lines'][i],58,IVORY,'Bold',max_width=760),540,1015+i*105+dy+20*(1-lp),lp*fade,'center')
        for i,card in enumerate(self.c['cards']):
            colors=(RED,IVORY) if i%2==0 else (IVORY,GREEN)
            self.place_card(im,self.info_card(card['kicker'],card['value'],card.get('sub',''),*colors),t,card['start'],card['end'])
        return self.finish(im,t)


def ffmpeg():
    import imageio_ffmpeg
    return os.environ.get('FFMPEG') or imageio_ffmpeg.get_ffmpeg_exe()


def make_renderer(source,content):return MotionSpace(source,content,ROOT/'assets/brand')


def stills(outdir,source,content):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True);r=make_renderer(source,content);r.credit=r.make_credit()
    for t in [.15,.5,1.35,3.0,6.1,8.2,11.7,15.0,19.2,21.9,24.1,26.2,27.7]:
        r.render(t).save(outdir/f'frame_{t:05.2f}.jpg',quality=94)
    r.src.close()


def picture(outdir,source,content):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True);r=make_renderer(source,content);r.credit=r.make_credit()
    ff=ffmpeg();silent=outdir/'picture.mp4'
    cmd=[ff,'-y','-hide_banner','-loglevel','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(silent)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for n in range(FRAMES):
            proc.stdin.write(r.render(n/FPS).tobytes())
            if n%120==0:print(f'Render {n}/{FRAMES}',flush=True)
    finally:proc.stdin.close()
    if proc.wait():raise RuntimeError('Video encoding failed')
    r.src.close();print(silent,flush=True)


if __name__=='__main__':
    import json
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['stills','picture'],default='stills');ap.add_argument('--outdir',required=True)
    ap.add_argument('--spec',required=True);ap.add_argument('--source',required=True)
    a=ap.parse_args();content=json.loads(Path(a.spec).read_text(encoding='utf-8'))
    stills(a.outdir,a.source,content) if a.mode=='stills' else picture(a.outdir,a.source,content)
