#!/usr/bin/env python3
"""One-time creation of the shared golden visual outro; NOT run per project.

Rebuild only with the brand owner's approval, then update the brand manifest.
The source-specific attribution remains on the main video, not in this reusable asset.
"""
from pathlib import Path
import argparse,subprocess
from PIL import Image
import render_motion as golden

ROOT=Path(__file__).resolve().parent.parent
DEFAULT=ROOT/'assets/outro/motion_v2_golden_outro.mp4'

def build(destination,force=False):
    destination=Path(destination)
    if destination.exists() and not force:raise ValueError('Outro already exists; use --force only for an approved rebuild')
    destination.parent.mkdir(parents=True,exist_ok=True)
    r=golden.MotionSpace.__new__(golden.MotionSpace)
    r.c={'source_credit':'مذكور داخل الفيديو'};r.brand=ROOT/'assets/brand'
    r.cairo=str(r.brand/'Cairo.ttf');r.inter=str(r.brand/'Inter.ttf')
    r.icon=Image.open(r.brand/'logo_icon.png').convert('RGBA');r.wm=Image.open(r.brand/'logo_wordmark.png').convert('RGBA')
    r.cache={};r.tiles={};r.fit={};r.outro=r.make_outro()
    tmp=destination.with_name(destination.stem+'.tmp.mp4')
    cmd=[golden.ffmpeg(),'-y','-hide_banner','-loglevel','warning','-f','rawvideo','-pix_fmt','rgb24','-s',f'{golden.W}x{golden.H}','-r',str(golden.FPS),'-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(tmp)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for n in range(round((golden.DURATION-golden.SOURCE_END)*golden.FPS)):
            proc.stdin.write(r.render_outro(golden.SOURCE_END+n/golden.FPS).tobytes())
    finally:proc.stdin.close()
    if proc.wait():raise RuntimeError('Outro encoding failed')
    tmp.replace(destination)
    print('PREBUILT OUTRO:',destination,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(DEFAULT));p.add_argument('--force',action='store_true');a=p.parse_args()
    build(a.output,a.force)
