#!/usr/bin/env python3
"""Real Whisper + two Native Messaging hosts: cancel, checkpoint, resume, cache."""
import argparse
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import uuid
import base64
from fixture_vault import classic_profile
ROOT=Path(__file__).resolve().parents[1]

def encode(value):
    data=json.dumps(value).encode();return struct.pack('=I',len(data))+data
def read(stream):
    header=stream.read(4)
    if len(header)!=4:raise RuntimeError('Native host disconnected')
    size=struct.unpack('=I',header)[0];data=b''
    while len(data)<size:data+=stream.read(size-len(data))
    return json.loads(data)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--real',action='store_true');args=parser.parse_args()
    if not args.real:parser.error('--real ejecuta Whisper local con voz de prueba.')
    out=ROOT/'.test-artifacts/recovery';out.mkdir(parents=True,exist_ok=True);run=Path(tempfile.mkdtemp(prefix='run-',dir=out));vault=run/'Vault';(vault/'02_Cerebro/Tech_&_Codigo').mkdir(parents=True)
    sys.path.insert(0,str(ROOT/'native'));from core import App
    app=App(run/'state');app.set_config({'vault':str(vault),'provider':'manual'});classic_profile(app);app.db.close()
    audio=run/'speech.flac';subprocess.run(['ffmpeg','-v','error','-y','-stream_loop','10','-i',str(ROOT/'.test-artifacts/jfk.flac'),'-t','75','-ar','16000',str(audio)],check=True)
    env={**os.environ,'ANACO_OB_STATE':str(run/'state')};host=subprocess.Popen([sys.executable,str(ROOT/'native/host.py')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,env=env)
    def request(value):
        host.stdin.write(encode(value));host.stdin.flush();events=[]
        while True:
            answer=read(host.stdout)
            if 'progress' in answer:events.append(answer['progress']);continue
            if not answer['ok']:raise RuntimeError(answer['error'])
            return answer['result'],events
    task=uuid.uuid4().hex
    try:
        raw=audio.read_bytes();value,_=request({'action':'upload_begin','name':'speech.flac','size':len(raw),'task':task});upload=value['upload']
        for offset in range(0,len(raw),393216):request({'action':'upload_chunk','upload':upload,'offset':offset,'data':base64.b64encode(raw[offset:offset+393216]).decode(),'task':task})
        host.stdin.write(encode({'action':'upload_finish','upload':upload,'task':task}));host.stdin.flush();cancelled=False;checkpoint=None
        while True:
            answer=read(host.stdout)
            p=answer.get('progress')
            if isinstance(p,dict) and p.get('processed_seconds',0)>0 and not cancelled:
                checkpoint=json.loads(next((run/'state/transcripts').glob('*.json')).read_text());assert not checkpoint['complete']
                control=subprocess.run([sys.executable,str(ROOT/'native/host.py')],input=encode({'action':'cancel_job','job':task}),capture_output=True,env=env,timeout=10);assert b'cancel_requested' in control.stdout
                cancelled=True;print('Cancelación solicitada tras',p['processed_seconds'],'s de audio.',flush=True)
            if 'ok' in answer:
                assert cancelled and not answer['ok'] and 'cancelado' in answer['error'];break
        saved_end=checkpoint['segments'][-1]['end'];result,events=request({'action':'upload_finish','upload':upload,'task':uuid.uuid4().hex})
        resumed=[v for v in events if isinstance(v,dict) and v.get('stage')=='transcribe' and v.get('processed_seconds',0)>0]
        assert resumed and resumed[0]['processed_seconds']>=saved_end
        final=json.loads(next((run/'state/transcripts').glob('*.json')).read_text());assert final['complete'] and len(final['segments'])>len(checkpoint['segments'])
        assert all(b['start']>=a['end']-.05 for a,b in zip(final['segments'],final['segments'][1:]))
        cached,events=request({'action':'upload_finish','upload':upload,'task':uuid.uuid4().hex});assert not any(isinstance(v,dict) and v.get('stage')=='transcribe' for v in events)
        report={'passed':True,'real_whisper':True,'native_cancel_control':True,'source_seconds':75,'checkpoint_segments':len(checkpoint['segments']),'resumed_at_seconds':resumed[0]['processed_seconds'],'final_segments':len(final['segments']),'completed_cache_reused':True,'timestamps_monotonic':True,'state':str(run/'state')}
        (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    finally:host.terminate();host.wait(timeout=10)
if __name__=='__main__':main()
