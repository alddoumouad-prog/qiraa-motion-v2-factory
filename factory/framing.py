#!/usr/bin/env python3
"""Bounded, sampled face-aware framing assistance, not a safety guarantee."""
from __future__ import annotations
import math, os, statistics
from pathlib import Path
import cv2

OUT_W,OUT_H=1080,1920
ASPECT=OUT_W/OUT_H

def crop_rect(width,height,centering_x):
    """Source pixels retained by Pillow ImageOps.fit for centering=(x,.5)."""
    centering_x=max(0.,min(1.,float(centering_x)))
    if width/height>=ASPECT:
        cw=height*ASPECT;ch=height
        return ((width-cw)*centering_x,0.,cw,ch)
    cw=width;ch=width/ASPECT
    return (0.,(height-ch)*.5,cw,ch)

def project_box(box,width,height,centering_x):
    x,y,w,h=box;cx,cy,cw,ch=crop_rect(width,height,centering_x)
    return ((x-cx)*OUT_W/cw,(y-cy)*OUT_H/ch,w*OUT_W/cw,h*OUT_H/ch)

def overlap_fraction(box,rect):
    x,y,w,h=box;left,top,right,bottom=rect
    if w<=0 or h<=0:return 0.
    area=max(0.,min(x+w,right)-max(x,left))*max(0.,min(y+h,bottom)-max(y,top))
    return area/(w*h)

def visible_fraction(box):return overlap_fraction(box,(0,0,OUT_W,OUT_H))

def desired_centering(width,height,source_face_center_x):
    if width/height<=ASPECT+1e-6:return .5
    crop_w=height*ASPECT;room=width-crop_w
    return max(0.,min(1.,(source_face_center_x-crop_w/2)/room))

def centering_at(t,track,default=.5):
    if not track:return default
    if t<=track[0]['time']:return track[0]['x']
    for a,b in zip(track,track[1:]):
        if t<=b['time']:
            f=(t-a['time'])/(b['time']-a['time'])
            return a['x']+(b['x']-a['x'])*f
    return track[-1]['x']

def overlaps(boxes,spec,mode,position,brand_position='right',metadata_position='right',brand_scale='standard'):
    """Flag detected face/head occlusion at sampled instants; unobserved frames remain unknown."""
    result=[];height=190 if mode=='scene' else 260;y=865 if position=='upper' else (1370 if mode=='golden' else 1310)
    for item in boxes:
        t=item['time'];box=item['projected'];regions=[]
        brand_rect=((700,35,1023,130) if brand_position=='right' else (60,35,383,130)) if brand_scale=='compact' else ((540,110,1000,245) if brand_position=='right' else (80,110,540,245))
        if t>=.65:regions.append(('brand',brand_rect))
        if 1.0<=t<5.05:regions.append(('metadata',(610,300,1010,438) if metadata_position=='right' else (80,300,480,438)))
        if .65<=t<5.22:regions.append(('opening_headline',(100,980,980,1360)))
        for c in spec['cards']:
            if float(c['start'])<=t<float(c['end']):regions.append(('card',(100,y,980,y+height)))
        for m in spec['micro']:
            if float(m['start'])<=t<float(m['start'])+2:regions.append(('micro',(180,1540,900,1664)))
        if visible_fraction(box)<.80:result.append({'time':t,'region':'crop','overlap':round(1-visible_fraction(box),3)})
        for name,rect in regions:
            x,yb,w,h=box
            target=(x-.10*w,yb-.25*h,1.20*w,1.25*h) if name=='brand' else box
            ratio=overlap_fraction(target,rect)
            if ratio>=(.025 if name=='brand' else .10):result.append({'time':t,'region':name,'overlap':round(ratio,3)})
    return result

def analyze(source,spec,plan):
    cap=cv2.VideoCapture(str(source));width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not cap.isOpened() or width<1 or height<1:
        cap.release();raise ValueError('Could not inspect source for framing')
    times=[1.5,3.0,6.5,10.0,15.0,19.0,22.0]
    times += [(float(c['start'])+float(c['end']))/2 for c in spec['cards']]
    times += [float(m['start'])+.8 for m in spec['micro']]
    times=sorted({round(t,2) for t in times if .1<=t<23.5})
    path=os.path.join(getattr(cv2.data,'haarcascades',''),'haarcascade_frontalface_default.xml')
    detector=cv2.CascadeClassifier(path);detector_ready=not detector.empty()
    found=[];decoded=0;multi_face_frames=0
    if detector_ready:
        for t in times:
            cap.set(cv2.CAP_PROP_POS_MSEC,t*1000);ok,frame=cap.read()
            if not ok:continue
            decoded+=1
            scale=min(1.,720./width);img=cv2.resize(frame,None,fx=scale,fy=scale) if scale<1 else frame
            gray=cv2.equalizeHist(cv2.cvtColor(img,cv2.COLOR_BGR2GRAY))
            faces=detector.detectMultiScale(gray,scaleFactor=1.1,minNeighbors=5,minSize=(35,35))
            if len(faces):
                if len(faces)>1:multi_face_frames+=1
                x,y,w,h=max(faces,key=lambda f:int(f[2])*int(f[3]));found.append({'time':t,'source_box':[float(x)/scale,float(y)/scale,float(w)/scale,float(h)/scale]})
    cap.release()
    crop=plan['crop'];reason='explicit center';track=[]
    if crop=='left':centering=0.;reason='explicit left'
    elif crop=='right':centering=1.;reason='explicit right'
    elif crop=='auto' and len(found)>=2:
        track=[{'time':f['time'],'x':round(desired_centering(width,height,f['source_box'][0]+f['source_box'][2]/2),6)} for f in found]
        centering=statistics.median(item['x'] for item in track);reason='sampled largest face with linear crop interpolation'
    elif crop=='auto':centering=.5;reason='insufficient detected faces; center fallback'
    else:centering=.5
    projected=[{'time':i['time'],'projected':project_box(i['source_box'],width,height,centering_at(i['time'],track,centering))} for i in found]
    brand_position='right';brand_scale='standard';metadata_position='right'
    if plan['mode']!='golden' and projected:
        def region_score(region,brand,meta,scale='standard'):
            return sum(item['overlap'] for item in overlaps(projected,spec,plan['mode'],'lower',brand,meta,scale) if item['region']==region)
        candidates=[('right','standard'),('left','standard'),('right','compact'),('left','compact')]
        # Preserve the full-size right logo unless a different candidate has materially fewer overlaps.
        baseline=region_score('brand','right','right');best=min(candidates,key=lambda q:region_score('brand',q[0],'right',q[1]))
        if region_score('brand',best[0],'right',best[1])+.05<baseline:brand_position,brand_scale=best
        if region_score('metadata',brand_position,'left',brand_scale)+.05<region_score('metadata',brand_position,'right',brand_scale):metadata_position='left'
    pos=plan['card_position'];requested=pos
    if pos=='auto':
        low=overlaps(projected,spec,plan['mode'],'lower',brand_position,metadata_position,brand_scale);up=overlaps(projected,spec,plan['mode'],'upper',brand_position,metadata_position,brand_scale)
        def card_score(x):return sum(item['overlap'] for item in x if item['region']=='card')
        pos='upper' if card_score(up)+.05<card_score(low) else 'lower'
    conflicts=overlaps(projected,spec,plan['mode'],pos,brand_position,metadata_position,brand_scale)
    warnings=[]
    if not detector_ready:warnings.append('face detector unavailable; framing and occlusion require manual review')
    elif not found:warnings.append('no face detected in sampled frames; does not prove the shot has no face')
    elif len(found)<2 and crop=='auto':warnings.append('insufficient face detections for auto framing; using centered crop')
    if multi_face_frames:warnings.append('multiple faces detected in some samples; the largest face is only a heuristic and may not be the speaker')
    if conflicts:warnings.append('possible face crop or overlay collision in sampled frames; inspect the actual video')
    warnings.append('face detection samples frames only; text overlays, all faces and all frames are not automatically guaranteed')
    return {'detector':'opencv_haar_frontalface_default','detector_available':detector_ready,'sample_times':times,
            'decoded_samples':decoded,'face_detections':len(found),'multi_face_samples':multi_face_frames,'source_size':[width,height],
            'crop_request':crop,'crop_centering_x':round(centering,6),'crop_track':track,'crop_reason':reason,
            'card_position_request':requested,'card_position':pos,'brand_position':brand_position,'brand_scale':brand_scale,'metadata_position':metadata_position,
            'sampled_conflicts':conflicts,'warnings':warnings,
            'guarantee':'heuristic samples only; human visual review required'}
