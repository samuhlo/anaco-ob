#!/usr/bin/env python3
"""Optional CPU-only ASR worker, in a separate venv. No audio leaves the machine."""
import argparse
import json
import time
import os
from pathlib import Path
from faster_whisper import WhisperModel

parser=argparse.ArgumentParser();parser.add_argument("file",nargs="?");parser.add_argument("--model",default="base");parser.add_argument("--cache",required=True);parser.add_argument('--progress',action='store_true');parser.add_argument('--checkpoint')
args=parser.parse_args()
def emit(value):print(json.dumps(value,ensure_ascii=False),flush=True)
def progress(**value):
    if args.progress:emit({'event':'progress','engine':'Whisper '+args.model+' · CPU',**value})
saved=json.loads(Path(args.checkpoint).read_text()) if args.checkpoint and Path(args.checkpoint).exists() else {}
def checkpoint(value):
    if not args.checkpoint:return
    path=Path(args.checkpoint);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700);temp=path.with_suffix('.part')
    temp.write_text(json.dumps(value,ensure_ascii=False));temp.chmod(0o600);os.replace(temp,path)
if saved.get('complete'):
    emit({'event':'result','result':saved} if args.progress else saved);raise SystemExit(0)
progress(stage='model',message='Cargando el modelo de transcripción local…')
model=WhisperModel(args.model,device="cpu",compute_type="int8",cpu_threads=6,download_root=args.cache)
if args.file:
    progress(stage='transcribe',message='Analizando voz e idioma en el equipo…')
    result=saved.get('segments',[]);resume=result[-1]['end'] if result else 0
    segments,info=model.transcribe(args.file,beam_size=3,vad_filter=not resume,clip_timestamps=str(resume),language=saved.get('language'))
    started=time.monotonic()
    progress(stage='transcribe',message='Reanudando desde el último segmento…' if resume else 'Transcribiendo en el equipo…',processed_seconds=resume,total_seconds=info.duration,elapsed_seconds=0)
    for s in segments:
        result.append({'start':s.start,'end':s.end,'text':s.text.strip()})
        checkpoint({'language':info.language,'segments':result,'duration':info.duration,'complete':False})
        progress(stage='transcribe',message='Transcribiendo en el equipo…',processed_seconds=min(s.end,info.duration),total_seconds=info.duration,elapsed_seconds=round(time.monotonic()-started,1))
    value={'language':info.language,'segments':result,'duration':info.duration,'complete':True};checkpoint(value)
    emit({'event':'result','result':value} if args.progress else value)
else:emit({"ready":True,"model":args.model})
