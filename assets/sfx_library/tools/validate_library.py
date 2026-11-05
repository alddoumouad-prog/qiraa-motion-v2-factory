#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import hashlib,json,wave
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def peak24(path):
 with wave.open(str(path),'rb') as w:
  raw=w.readframes(w.getnframes());channels=w.getnchannels()
 b=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3).astype(np.int32)
 v=b[:,0]|(b[:,1]<<8)|(b[:,2]<<16);v=np.where(v&0x800000,v-(1<<24),v)
 return 20*np.log10((np.max(np.abs(v))+1e-9)/8388608)

def main():
 data=json.loads((ROOT/'library.json').read_text());items=data['items']
 assert len(items)==120 and data['count']==120
 counts=Counter(i['category'] for i in items)
 assert len(counts)==12 and set(counts.values())=={10},counts
 ids=[i['id'] for i in items];assert len(set(ids))==len(ids)
 wav_hashes=[]
 for item in items:
  wav=ROOT/item['wav'];mp3=ROOT/item['mp3'];assert wav.is_file() and mp3.is_file(),item['id']
  with wave.open(str(wav),'rb') as w:
   assert w.getframerate()==48000 and w.getsampwidth()==3 and w.getnchannels()==item['channels'],item['id']
   duration=w.getnframes()/w.getframerate()
  assert abs(duration*1000-item['duration_ms'])<=1,item['id']
  peak=peak24(wav);assert abs(peak-(-15))<.12,(item['id'],peak)
  assert mp3.stat().st_size>1000,item['id']
  wav_hashes.append(hashlib.sha256(wav.read_bytes()).hexdigest())
 assert len(set(wav_hashes))==120,'Duplicate WAV assets found'
 manifest=(ROOT/'manifest.sha256').read_text().splitlines();assert len(manifest)==240
 print(json.dumps({'status':'passed','sounds':len(items),'categories':len(counts),'wav_files':len(wav_hashes),'mp3_files':len(items),'sample_rate':48000,'bit_depth':24,'peak_dbfs':-15,'duplicates':0},indent=2))
if __name__=='__main__':main()
