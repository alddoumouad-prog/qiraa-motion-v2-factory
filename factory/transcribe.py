#!/usr/bin/env python3
"""Generate word-level timestamps from a source file (timestamps are in source time)."""
import argparse, json, subprocess
from pathlib import Path
import imageio_ffmpeg
import numpy as np
from faster_whisper import WhisperModel

p=argparse.ArgumentParser()
p.add_argument('--source',required=True,help='Downloaded local video or audio')
p.add_argument('--output',required=True,help='Path to transcript_words.json')
p.add_argument('--model',default='base',help='Whisper model (base for multilingual, base.en for English)')
p.add_argument('--language',default=None,help='Optional language code, e.g. en')
a=p.parse_args()
# Decode explicitly to avoid PyAV/faster-whisper API version mismatches.
raw=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-i',a.source,'-vn','-ac','1','-ar','16000','-f','f32le','-'],check=True,capture_output=True).stdout
audio=np.frombuffer(raw,dtype='<f4').copy()
if not len(audio):raise SystemExit('Source has no decodable audio')
model=WhisperModel(a.model,device='cpu',compute_type='int8')
segments,info=model.transcribe(audio,language=a.language,word_timestamps=True,vad_filter=True)
result=[]
for s in segments:
    result.append({'start':s.start,'end':s.end,'text':s.text.strip(),
        'words':[{'start':w.start,'end':w.end,'word':w.word} for w in (s.words or [])]})
dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Wrote {dest} ({len(result)} segments, detected language: {info.language})')
