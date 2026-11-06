#!/usr/bin/env python3
"""Verify and append the approved reusable outro without re-encoding video."""
from pathlib import Path
import subprocess
import cv2
import render_motion as golden

ROOT=Path(__file__).resolve().parent.parent
OUTRO=ROOT/'assets/outro/motion_v2_golden_outro.mp4'
MAIN_FRAMES=round(golden.SOURCE_END*golden.FPS)
OUTRO_FRAMES=golden.FRAMES-MAIN_FRAMES

def check_asset(path=OUTRO):
    path=Path(path)
    if not path.is_file():raise ValueError('Approved reusable outro is missing; do not silently regenerate it')
    cap=cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():raise ValueError('Cannot decode the reusable outro')
        width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps=cap.get(cv2.CAP_PROP_FPS);frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        ok,_=cap.read()
        if not ok or (width,height,round(fps,3),frames)!=(golden.W,golden.H,float(golden.FPS),OUTRO_FRAMES):
            raise ValueError('Reusable outro format mismatch')
    finally:cap.release()
    return {'asset':'assets/outro/motion_v2_golden_outro.mp4','frames':frames,'fps':fps,'duration_seconds':frames/fps,'method':'pre-rendered outro; concat video stream copy'}

def concat(main,outro,destination):
    """Concat compatible H.264 segments by copying packets, not decoding/re-rendering."""
    main=Path(main).resolve();outro=Path(outro).resolve();destination=Path(destination).resolve()
    def escaped(p):
        value=str(p)
        if '\n' in value or '\r' in value:raise ValueError('Line breaks in paths are not supported')
        return "file '"+value.replace("'","'\\''")+"'\n"
    listing=destination.parent/'concat_video.txt';listing.write_text(escaped(main)+escaped(outro),encoding='utf-8')
    subprocess.run([golden.ffmpeg(),'-y','-hide_banner','-loglevel','error','-f','concat','-safe','0','-i',str(listing),'-map','0:v:0','-an','-c:v','copy','-movflags','+faststart',str(destination)],check=True)
    return destination
