"""Cooperative jobs, controlled through a separate Native Messaging connection."""
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time
from core import UserError,json_dump
from translation import t

class Cancelled(UserError):
    def __init__(self):super().__init__(t('Trabajo cancelado. Puedes reanudarlo desde Trabajos recuperables.'))

def running(value):
    if value.get('status')!='running':return False
    pid=value.get('pid')
    if not isinstance(pid,int) or pid<=0:return False
    try:os.kill(pid,0)
    except ProcessLookupError:return False
    except PermissionError:return True
    except (OSError,ValueError):return False
    return True

class Job:
    def __init__(self,app,identifier):
        if not re.fullmatch(r'[a-f0-9-]{32,36}',str(identifier)):raise UserError('Trabajo no válido.')
        self.app=app;self.directory=app.state/'jobs'/identifier;self.directory.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.path=self.directory/'job.json'
        self.vault = str(app.vault())
    def load(self):
        value=json.loads(self.path.read_text()) if self.path.exists() else {'id':self.directory.name,'vault':self.vault,'started':time.time()}
        if value['vault']!=self.vault:raise UserError('El trabajo pertenece a otro vault.')
        return value
    def update(self,**values):
        value=self.load();value.update(values,updated=time.time());json_dump(self.path,value);return value
    def check(self):
        if (self.directory/'cancel').exists():raise Cancelled()
    def check_vault(self):
        if self.vault != str(self.app.vault()):raise UserError('El trabajo pertenece a otro vault.')
    def start(self,message):
        self.check_vault();self.check();self.update(status='running',pid=os.getpid(),action=message.get('action'),request={k:v for k,v in message.items() if k not in ('requestId','data','capture')})
    def cancel(self):
        self.check_vault();self.load();(self.directory/'cancel').touch(mode=0o600);return {'cancel_requested':True}
    def assert_inactive(self):
        self.check_vault()
        if running(self.load()):raise UserError('El trabajo sigue en curso. Cancélalo antes de descartarlo.')
    def discard(self):
        self.assert_inactive();self.update(status='discarded');return {'discarded':True}
    def resume(self):
        self.check_vault()
        value=self.load()
        if value.get('status') in ('complete','discarded'):raise UserError('Este trabajo ya no está pendiente.')
        if value.get('action') not in ('upload_finish','draft','video_url'):raise UserError('Repite la extracción desde la página original; sus páginas recibidas se conservan.')
        (self.directory/'cancel').unlink(missing_ok=True)
        self.update(status='pending');return value['request']

def capture_jobs(app,identifier):
    result=[]
    for path in (app.state/'jobs').glob('*/job.json'):
        try:
            value=json.loads(path.read_text())
            if value.get('vault')==str(app.vault()) and value.get('action')=='draft' and value.get('request',{}).get('id')==identifier and value.get('status') not in ('complete','discarded'):
                result.append(Job(app,path.parent.name))
        except (OSError,ValueError):continue
    return result

def pending(app):
    result=[]
    for path in (app.state/'jobs').glob('*/job.json'):
        try:
            value=json.loads(path.read_text())
            if value.get('vault')!=str(app.vault()) or value.get('status') in ('complete','discarded'):continue
            if value.get('status')=='running' and not running(value):value['status']='interrupted'
            if value.get('action') in ('upload_finish','draft','video_url'):
                result.append({k:value.get(k) for k in ('id','action','status','updated')})
        except (OSError,ValueError):continue
    return sorted(result,key=lambda v:v.get('updated') or 0,reverse=True)[:20]

def run_command(command,check,timeout=300,input=None,text=False):
    """Kill the process group, including downloader/ffmpeg children, on cancellation."""
    process=subprocess.Popen(command,stdin=subprocess.PIPE if input is not None else None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=text,start_new_session=True)
    deadline=time.monotonic()+timeout;data=input
    try:
        while True:
            check()
            if time.monotonic()>deadline:raise subprocess.TimeoutExpired(command,timeout)
            try:
                out,err=process.communicate(input=data,timeout=min(.2,max(.01,deadline-time.monotonic())))
                return subprocess.CompletedProcess(command,process.returncode,out,err)
            except subprocess.TimeoutExpired:data=None
    finally:
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGKILL);process.communicate()
