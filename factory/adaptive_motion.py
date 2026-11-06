#!/usr/bin/env python3
"""Three bounded creative layouts for Motion V2; golden stays in render_motion.

All layouts reuse the approved logo, wordmark, type, palette, SFX and timing
contract. Face analysis is heuristic and is not a guarantee of safe framing.
"""
from pathlib import Path
import subprocess
import cv2
from PIL import Image,ImageDraw,ImageOps
import render_motion as golden
import framing

base=golden.base
W,H,FPS,DURATION,SOURCE_END,FRAMES=golden.W,golden.H,golden.FPS,golden.DURATION,golden.SOURCE_END,golden.FRAMES
RED,IVORY,GREEN,GREEN_2=golden.RED,golden.IVORY,golden.GREEN,golden.GREEN_2

class AdaptiveMotion(golden.MotionSpace):
    def __init__(self,source,content,brand,plan,analysis):
        self.plan=plan;self.analysis=analysis;self.mode=plan['mode']
        self.crop_x=float(analysis['crop_centering_x']);self.card_position=analysis['card_position']
        super().__init__(source,content,brand)

    def fitted(self,t):
        src=self.src.get(t);crop_x=framing.centering_at(t,self.analysis.get('crop_track',[]),self.crop_x)
        k=(self.src.key,round(crop_x,4))
        if k not in self.fit:
            if len(self.fit)>4:self.fit.clear()
            self.fit[k]=ImageOps.fit(src,(W,H),Image.Resampling.LANCZOS,centering=(crop_x,.5)).convert('RGBA')
        return self.fit[k].copy()

    def make_brand(self):
        original=super().make_brand();position=self.analysis.get('brand_position','right');scale=self.analysis.get('brand_scale','standard')
        if scale=='standard' and position=='right':return original
        out=Image.new('RGBA',(W,H),(0,0,0,0))
        if scale=='compact':
            tile=original.crop((540,110,1001,245)).resize((323,95),Image.Resampling.LANCZOS)
            out.paste(tile,(700 if position=='right' else 60,35))
        else:out.paste(original.crop((540,0,1001,H)),(80,0))
        return out

    def make_meta(self):
        original=super().make_meta()
        if self.analysis.get('metadata_position','right')=='right':return original
        out=Image.new('RGBA',(W,H),(0,0,0,0));out.paste(original.crop((610,0,1011,H)),(80,0));return out

    def make_opening(self):
        cap=cv2.VideoCapture(str(self.src.path));cap.set(cv2.CAP_PROP_POS_MSEC,3000);ok,fr=cap.read();cap.release()
        if not ok:raise ValueError('Cannot decode source at opening frame')
        crop_x=framing.centering_at(3.0,self.analysis.get('crop_track',[]),self.crop_x)
        src=Image.fromarray(cv2.cvtColor(fr,cv2.COLOR_BGR2RGB));bg=ImageOps.fit(src,(W,H),Image.Resampling.LANCZOS,centering=(crop_x,.5)).convert('RGBA')
        bg=Image.alpha_composite(bg,Image.new('RGBA',(W,H),base.rgba(GREEN,215)))
        rings=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(rings)
        for r,a in [(120,170),(220,120),(330,85),(450,50)]:d.ellipse((540-r,1090-r,540+r,1090+r),outline=base.rgba(RED,a),width=4)
        bg=Image.alpha_composite(bg,rings)
        icon=self.icon.resize((145,145),Image.Resampling.LANCZOS);bg.paste(icon,(468,1018),icon)
        wm=self.wm.resize((340,137),Image.Resampling.LANCZOS);bg.paste(wm,(370,1190),wm)
        return bg

    def pill(self,text,fill,text_color):
        if self.mode=='golden':return super().pill(text,fill,text_color)
        im=Image.new('RGBA',(960,140),(0,0,0,0));d=ImageDraw.Draw(im)
        if self.mode=='quote':
            d.rounded_rectangle((0,0,959,139),radius=28,fill=base.rgba(IVORY));d.rounded_rectangle((0,0,14,139),radius=7,fill=base.rgba(RED));color=GREEN
        elif self.mode=='scene':
            d.rounded_rectangle((0,0,959,139),radius=28,fill=base.rgba(GREEN,242));d.rounded_rectangle((0,0,14,139),radius=7,fill=base.rgba(RED));color=IVORY
        else:
            d.rounded_rectangle((0,0,959,139),radius=22,fill=base.rgba(fill));d.rectangle((0,100,18,139),fill=base.rgba(RED if fill==IVORY else IVORY));color=text_color
        tile=self.tile_fit(text,44,color,max_width=850)
        if tile.width>850:raise ValueError('Creative opening line is too wide; shorten it')
        self.paste(im,tile,480,35,1,'center');return im

    def info_card(self,kicker,value,sub='',fill=RED,text_color=IVORY):
        if self.mode=='golden':return super().info_card(kicker,value,sub,fill,text_color)
        key=('adaptive',self.mode,kicker,value,sub,fill,text_color)
        if key in self.cache:return self.cache[key]
        height=190 if self.mode=='scene' else 260
        im=Image.new('RGBA',(880,height),(0,0,0,0));d=ImageDraw.Draw(im)
        if self.mode=='quote':
            d.rounded_rectangle((0,0,879,259),radius=26,fill=base.rgba(fill));d.rectangle((0,0,14,259),fill=base.rgba(GREEN if fill==IVORY else IVORY))
            d.ellipse((34,30,54,50),fill=base.rgba(text_color));d.ellipse((64,30,84,50),fill=base.rgba(text_color))
            color=text_color;value_size=58;kicker_y=25;value_y=82;sub_y=190;limit=745
        elif self.mode=='scene':
            d.rounded_rectangle((0,0,879,189),radius=26,fill=base.rgba(GREEN,238));d.rounded_rectangle((0,0,13,189),radius=6,fill=base.rgba(RED))
            color=IVORY;value_size=50;kicker_y=10;value_y=51;sub_y=145;limit=750
        else:
            d.rounded_rectangle((0,0,879,259),radius=30,fill=base.rgba(GREEN));d.rounded_rectangle((22,22,858,72),radius=16,fill=base.rgba(RED))
            color=IVORY;value_size=56;kicker_y=23;value_y=94;sub_y=193;limit=750
        for text,size,y,weight,alpha in [(kicker,25,kicker_y,'Medium',1),(value,value_size,value_y,'Bold',1),(sub,24,sub_y,'Regular',.86)]:
            if not text:continue
            tile=self.tile_fit(text,size,color,weight,max_width=limit)
            if tile.width>limit:raise ValueError('Creative card text exceeds safe width; shorten it')
            self.paste(im,tile,842,y,alpha,'right')
        self.cache[key]=im;return im

    def place_card(self,im,card,t,start,end,y=1370):
        if self.mode=='golden' and self.card_position=='lower':return super().place_card(im,card,t,start,end,y)
        y=865 if self.card_position=='upper' else (1370 if self.mode=='golden' else 1310)
        enter=golden.ease01(t,start,.32);exitp=base.clamp((t-(end-.35))/.35) if t>end-.35 else 0;op=enter*(1-exitp)
        if op<=0:return
        if self.mode=='quote':self.paste(im,card,100+38*(1-enter)+20*exitp,y,op)
        elif self.mode=='scene':self.paste(im,card,100-45*(1-enter)-20*exitp,y,op)
        else:self.paste(im,card,100,y+35*(1-enter)+30*exitp,op)

    def render(self,t):
        if self.mode=='golden':return super().render(t)
        if t>=SOURCE_END:return self.render_outro(t)
        current=self.fitted(t)
        if t<.65:
            op=1 if t<.55 else 1-(t-.55)/.1;im=Image.blend(current,self.opening,base.clamp(op))
            for i,start in enumerate([.05,.17,.29]):
                p=golden.ease01(t,start,.2);txt=self.c['headline_lines'][i];fill=IVORY if i==0 else RED;tc=GREEN if i==0 else IVORY
                if p>0:self.paste(im,self.pill(txt,fill,tc),60,540+i*160+60*(1-p),p*base.clamp(op))
        else:im=current
        self.paste(im,self.brand_layer,0,0,golden.ease01(t,.65,.30))
        meta_op=golden.ease01(t,1.0,.30)
        if t>4.7:meta_op*=1-base.clamp((t-4.7)/.35)
        self.paste(im,self.meta,0,0,meta_op);self.paste(im,self.credit,0,0,.78*golden.ease01(t,1.15,.35))
        if .65<=t<5.22:
            cp=golden.ease01(t,.65,.30);exitp=base.clamp((t-4.72)/.50) if t>4.72 else 0;op=cp*(1-exitp);dy=35*(1-cp)+30*exitp
            card=Image.new('RGBA',(880,380),(0,0,0,0));d=ImageDraw.Draw(card)
            if self.mode=='quote':
                d.rounded_rectangle((0,0,879,379),radius=32,fill=base.rgba(IVORY));d.rounded_rectangle((0,0,15,379),radius=7,fill=base.rgba(RED));tc=GREEN
            elif self.mode=='scene':
                d.rounded_rectangle((0,0,879,379),radius=28,fill=base.rgba(GREEN,232));d.rounded_rectangle((0,0,15,379),radius=7,fill=base.rgba(RED));tc=IVORY
            else:
                d.rounded_rectangle((0,0,879,379),radius=36,fill=base.rgba(RED));d.rounded_rectangle((22,22,858,34),radius=6,fill=base.rgba(IVORY));tc=IVORY
            self.paste(im,card,100,980+dy,op)
            for i,start in enumerate([.82,1.0,1.18]):
                lp=golden.ease01(t,start,.27);fade=1-base.clamp((t-4.70)/.40) if t>4.70 else 1
                if lp>0 and fade>0:
                    tile=self.tile_fit(self.c['headline_lines'][i],58,tc,'Bold',max_width=760)
                    if tile.width>760:raise ValueError('Creative headline is too wide; shorten it')
                    self.paste(im,tile,540,1015+i*105+dy+20*(1-lp),lp*fade,'center')
        for i,card in enumerate(self.c['cards']):
            colors=(RED,IVORY) if i%2==0 else (IVORY,GREEN)
            self.place_card(im,self.info_card(card['kicker'],card['value'],card.get('sub',''),*colors),t,card['start'],card['end'])
        return self.finish(im,t)


def make_renderer(source,content,plan,analysis):
    if plan['mode']=='golden' and plan['crop']=='center' and analysis['crop_centering_x']==.5 and analysis['card_position']=='lower':
        r=golden.make_renderer(source,content)
    else:r=AdaptiveMotion(source,content,golden.ROOT/'assets/brand',plan,analysis)
    r.credit=r.make_credit()
    return r

def preflight(renderer,content):
    """Render representative events to catch obvious layout overflow before encoding."""
    for t in [.15,1.35]+[float(x['start'])+.15 for x in content['cards']]+[float(x['start'])+.15 for x in content['micro']]:
        renderer.render(t)
    # No guarantee of detecting face occlusion or every font/codec issue.

def picture(outdir,source,content,plan,analysis):
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True);r=make_renderer(source,content,plan,analysis)
    try:
        preflight(r,content)
        ff=golden.ffmpeg();silent=outdir/'picture.mp4'
        cmd=[ff,'-y','-hide_banner','-loglevel','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(silent)]
        proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            for n in range(FRAMES):
                proc.stdin.write(r.render(n/FPS).tobytes())
                if n%120==0:print(f'Render {n}/{FRAMES}',flush=True)
        finally:proc.stdin.close()
        if proc.wait():raise RuntimeError('Video encoding failed')
    finally:r.src.close()
    print(silent,flush=True)
