#!/usr/bin/env python3
"""Download a public source and transcribe it on a temporary runner."""
import os, re, subprocess, sys
from pathlib import Path
from urllib.parse import urlparse
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parent.parent
url=os.environ.get('SOURCE_URL','').strip();language=os.environ.get('LANGUAGE','').strip()
parsed=urlparse(url)
if parsed.scheme not in ('http','https') or not parsed.netloc:raise SystemExit('SOURCE_URL must be an http(s) URL')
if parsed.username or parsed.password:raise SystemExit('Never put credentials in a URL')
if language and not re.fullmatch('[a-z]{2,3}',language):raise SystemExit('LANGUAGE must be a 2–3 letter code or empty')
work=ROOT/'work';work.mkdir(exist_ok=True);out=ROOT/'transcript_output';out.mkdir(exist_ok=True)
subprocess.run([sys.executable,'-m','yt_dlp','--no-playlist','--no-progress','--restrict-filenames','--ffmpeg-location',imageio_ffmpeg.get_ffmpeg_exe(),'-f','bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best','--merge-output-format','mp4','-o',str(work/'input.%(ext)s'),url],check=True)
files=[p for p in work.glob('input.*') if p.suffix.lower() in ('.mp4','.mkv','.mov','.webm')]
if len(files)!=1:raise SystemExit('Expected one downloaded video')
args=[sys.executable,str(ROOT/'factory/transcribe.py'),'--source',str(files[0]),'--output',str(out/'transcript_words.json'),'--model','base']
if language:args+=['--language',language]
subprocess.run(args,check=True)
print('Transcript created. The source video is not included in the artifact.')
