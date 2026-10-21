"""PDF, subtitle and local speech processing. Called only for selected resources."""
from __future__ import annotations
import base64
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import os
import selectors
import tempfile
import time
import hashlib
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen
from core import UserError, ROOT, clean, json_dump, normalized_url
from translation import n, t

MAX_FILE = 100_000_000
MAX_TRANSCRIPT = 400_000  # four hours of speech fit with room to spare


def media_venv(app):
    """The transcription environment: a development checkout's, else the state folder's."""
    development = ROOT / ".media-venv"
    return development if development.is_dir() else app.state / "media-venv"

def run_progress(command,progress,timeout=1800,check=lambda:None):
    """Consume private worker JSONL, forwarding progress metadata only."""
    with tempfile.TemporaryFile() as errors:
        try:process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=errors)
        except FileNotFoundError as exc:raise UserError('No encuentro el motor local de transcripción.') from exc
        result=None;buffer=b'';deadline=time.monotonic()+timeout
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout,selectors.EVENT_READ)
                while selector.get_map():
                    check()
                    if time.monotonic()>deadline:raise UserError('La transcripción local superó el tiempo máximo. Prueba Whisper tiny o un fragmento más corto.')
                    for key,_ in selector.select(min(0.5,max(0,deadline-time.monotonic()))):
                        chunk=os.read(key.fileobj.fileno(),65536)
                        if not chunk:selector.unregister(key.fileobj);continue
                        buffer+=chunk
                        if len(buffer)>16000000:raise UserError('La respuesta del motor local es demasiado grande.')
                        while b'\n' in buffer:
                            line,buffer=buffer.split(b'\n',1)
                            try:value=json.loads(line)
                            except ValueError:raise UserError('El motor local no devolvió una respuesta válida.')
                            if value.get('event')=='progress':
                                update={k:v for k,v in value.items() if k in ('stage','message','engine','processed_seconds','total_seconds','elapsed_seconds')}
                                # The worker writes Spanish; its texts are translated here.
                                if isinstance(update.get('message'),str):update['message']=t(update['message'])
                                progress(update)
                            elif value.get('event')=='result':result=value.get('result')
                process.wait(timeout=max(.1,deadline-time.monotonic()))
            if process.returncode or not isinstance(result,dict):raise UserError('No se pudo completar la transcripción local. Prueba Whisper tiny o importa subtítulos.')
            return result
        finally:
            if process.poll() is None:process.kill();process.wait()
            process.stdout.close()


def run(command, timeout=120,cancel=None):
    try:
        if cancel:
            from jobs import run_command
            result=run_command(command,cancel,timeout=timeout)
        else:result=subprocess.run(command,capture_output=True,timeout=timeout)
    except FileNotFoundError as exc:
        raise UserError("Falta una herramienta multimedia: {tool}. Ejecuta scripts/install-media.sh.", tool=command[0]) from exc
    except subprocess.TimeoutExpired as exc:
        raise UserError("El procesamiento multimedia superó el tiempo previsto. Prueba con un archivo o rango más corto.") from exc
    if result.returncode:
        raise UserError("No se ha podido procesar el recurso. Puede requerir sesión, estar protegido o tener un formato no compatible. Puedes importar el archivo o los subtítulos.")
    return result.stdout


def stamp(seconds):
    seconds=max(0,int(seconds));return f"{seconds//3600:02d}:{seconds%3600//60:02d}:{seconds%60:02d}" if seconds>=3600 else f"{seconds//60:02d}:{seconds%60:02d}"


def youtube_id(url):
    """The video id of a YouTube address, or None for any other source."""
    parts=urlsplit(str(url or ''));host=(parts.hostname or '').removeprefix('www.').removeprefix('m.')
    if host=='youtu.be':value=parts.path.strip('/').split('/')[0]
    elif host in ('youtube.com','music.youtube.com','youtube-nocookie.com'):
        found=re.match(r'/(?:shorts|live|embed)/([^/?#]+)',parts.path)
        value=found.group(1) if found else (parse_qs(parts.query).get('v') or [''])[0]
    else:return None
    return value if re.fullmatch(r'[A-Za-z0-9_-]{11}',value) else None


def link_times(text,url,duration=None):
    """Turn [mm:ss] marks into links that open the YouTube video at that second."""
    video=youtube_id(url)
    if not video:return text
    def replace(match):
        parts=[int(v) for v in match.group(1).split(':')];seconds=sum(v*60**i for i,v in enumerate(reversed(parts)))
        # MOTIVE -> a time past the end was invented or miscopied: keep it as plain text.
        if duration and seconds>duration:return match.group(0)
        return f"[{match.group(1)}](https://www.youtube.com/watch?v={video}&t={seconds}s)"
    return re.sub(r'(?<![\[!\w])\[((?:\d{1,2}:)?\d{1,2}:[0-5]\d)\](?!\()',replace,text)


def subtitles(text):
    """Parse SRT/VTT, retaining cue times and collapsing rolling caption overlap."""
    text=text.lstrip("\ufeff").replace("\r\n","\n")
    entries=[];previous=""
    for block in re.split(r"\n\s*\n",text):
        lines=block.splitlines();timing=next((i for i,line in enumerate(lines) if "-->" in line),None)
        if timing is None:continue
        match=re.match(r"\s*(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{3})\s*-->",lines[timing])
        if not match:continue
        content=html.unescape(re.sub(r"<[^>]*>",""," ".join(lines[timing+1:]))).strip()
        content=re.sub(r"\s+"," ",content)
        if not content or content==previous:continue
        words=content.split();old=previous.split();overlap=0
        for n in range(min(len(words),len(old)),0,-1):
            if old[-n:]==words[:n]:overlap=n;break
        addition=" ".join(words[overlap:])
        if addition:
            h,m,s,ms=match.groups();seconds=int(h or 0)*3600+int(m)*60+int(s)+int(ms)/1000
            entries.append({"start":seconds,"text":addition})
        previous=content
    if not entries:raise UserError("No se encontraron subtítulos válidos. Importa un archivo SRT o VTT con marcas temporales.")
    return entries


def page_range(value,total,limit):
    if not value:return list(range(1,min(total,limit)+1))
    result=set()
    for token in value.split(","):
        match=re.fullmatch(r"\s*(\d+)(?:\s*-\s*(\d+))?\s*",token)
        if not match:raise UserError("Usa un rango de páginas como 1-5,8,12.")
        start,end=int(match[1]),int(match[2] or match[1])
        if start<1 or end<start or end>total or end-start+1>limit:raise UserError("El rango no existe o supera el límite de páginas configurado.")
        result.update(range(start,end+1))
    if len(result)>limit:raise UserError("Selecciona menos páginas o aumenta el límite en Opciones.")
    return sorted(result)


class Media:
    def __init__(self,app):self.app=app
    def run(self,command,timeout=120):return run(command,timeout,cancel=self.app.check_cancel)

    def upload_dir(self,identifier):
        if not re.fullmatch(r"[a-f0-9]{32}",str(identifier)):raise UserError("Archivo temporal no válido.")
        return self.app.state/"uploads"/identifier

    def begin(self,message):
        size=message.get("size")
        name=Path(clean(message.get("name"),200)).name
        if message.get("purpose")=="asset":
            from embeds import ASSET_TYPES
            limit=ASSET_TYPES.get(Path(name).suffix.lower())
            if not limit:raise UserError("Tipo de recurso incrustado no admitido.")
            if type(size) is not int or not 0<size<=limit:raise UserError("El recurso supera el límite de {megabytes} MB.", megabytes=limit//1_000_000)
            identifier=uuid.uuid4().hex;directory=self.upload_dir(identifier);directory.mkdir(parents=True,mode=0o700)
            json_dump(directory/"meta.json",{"name":name,"size":size,"url":"","purpose":"asset"})
            (directory/"data.part").touch(mode=0o600)
            return {"upload":identifier}
        limit=MAX_FILE if Path(name).suffix.lower() in ('.pdf','.vtt','.srt') else 1_000_000_000
        if type(size) is not int or not 0<size<=limit:raise UserError("El archivo supera el límite: 100 MB para PDF/subtítulos y 1 GB para audio/vídeo local.")
        if Path(name).suffix.lower() not in (".pdf",".vtt",".srt",".mp3",".mp4",".m4a",".webm",".wav",".ogg",".flac",".mov"):
            raise UserError("Importa PDF, subtítulos SRT/VTT o un archivo de audio/vídeo compatible.")
        identifier=uuid.uuid4().hex;directory=self.upload_dir(identifier);directory.mkdir(parents=True,mode=0o700)
        json_dump(directory/"meta.json",{"name":name,"size":size,"url":clean(message.get("url"),8000)})
        (directory/"data.part").touch(mode=0o600)
        return {"upload":identifier}

    def chunk(self,message):
        directory=self.upload_dir(message.get("upload"));meta=json.loads((directory/"meta.json").read_text());path=directory/"data.part"
        try:raw=base64.b64decode(message.get("data",""),validate=True)
        except Exception as exc:raise UserError("Fragmento de archivo no válido.") from exc
        if len(raw)>524288 or message.get("offset")!=path.stat().st_size or path.stat().st_size+len(raw)>meta["size"]:
            raise UserError("La transferencia del archivo está incompleta o desordenada. Reintenta la importación.")
        with path.open("ab") as stream:stream.write(raw)
        return {"offset":path.stat().st_size}

    def finish_asset(self,message):
        from embeds import store_asset
        directory=self.upload_dir(message.get("upload"));meta=json.loads((directory/"meta.json").read_text());path=directory/"data.part"
        if meta.get("purpose")!="asset":raise UserError("La subida no corresponde a un recurso incrustado.")
        if not path.exists() or path.stat().st_size!=meta["size"]:raise UserError("Faltan fragmentos del recurso.")
        result=store_asset(self.app,path,Path(meta["name"]).suffix.lower());shutil.rmtree(directory,ignore_errors=True)
        return result

    def finish(self,message):
        directory=self.upload_dir(message.get("upload"));meta=json.loads((directory/"meta.json").read_text());path=directory/"data.part"
        suffix=Path(meta["name"]).suffix.lower();target=directory/("source"+suffix)
        if path.exists():
            if path.stat().st_size!=meta["size"]:raise UserError("Faltan fragmentos del archivo.")
            path.replace(target)
        if not target.exists():raise UserError('No se encuentra el archivo recibido para reanudarlo.')
        if target.stat().st_size!=meta['size']:raise UserError('El archivo recibido cambió; vuelve a importarlo para recuperar el contenido completo.')
        url=meta["url"] if meta["url"].startswith(("https://","http://")) else "local-file:"+meta["name"]
        if suffix==".pdf":return self.pdf(target,meta["name"],url,message.get("pages",""))
        if suffix in (".vtt",".srt"):
            return self.transcript_capture(subtitles(target.read_text(encoding="utf-8-sig",errors="replace")),meta["name"],url,n("Subtítulos importados por el usuario"),[],{"coverage":n("Archivo aportado; no se ha verificado contra la duración completa del vídeo")})
        return self.audio(target,meta["name"],url)

    def pdf(self,path,title,url,ranges=""):
        if b"%PDF-" not in path.read_bytes()[:1024]:raise UserError("El recurso no es un PDF. Puede ser una página de inicio de sesión.")
        info=self.run(["pdfinfo",str(path)]).decode(errors="replace")
        match=re.search(r"^Pages:\s+(\d+)",info,re.M)
        if not match:raise UserError("No se pudo obtener el número de páginas del PDF.")
        total=int(match[1]);cfg=self.app.config();pages=page_range(ranges,total,cfg["pdf_page_limit"])
        texts={p:self.run(["pdftotext","-f",str(p),"-l",str(p),"-layout",str(path),"-"]).decode(errors="replace").strip() for p in pages}
        budget=min(cfg["pdf_visual_pages"],len(pages))
        priorities=sorted(pages,key=lambda p:(bool(re.search(r"figura|diagram|figure|gr[aá]fic|esquema|table",texts[p],re.I)),len(texts[p])<100),reverse=True)
        # Ensure both ends are considered; the remaining pages favor diagrams/scans.
        visual=list(dict.fromkeys([pages[0],pages[-1]]+priorities))[:budget]
        images=[];warnings=[]
        for p in sorted(visual):
            prefix=path.parent/f"page-{p}"
            self.run(["pdftoppm","-f",str(p),"-l",str(p),"-scale-to","1600","-jpeg","-jpegopt","quality=82","-singlefile",str(path),str(prefix)])
            raw=prefix.with_suffix(".jpg").read_bytes()
            images.append({"data":base64.b64encode(raw).decode(),"alt":n("Página {page} del PDF",page=p),"page":p,"url":url+"#page="+str(p)})
            if len(texts[p])<40 and shutil.which("tesseract"):
                try:texts[p]=self.run(["tesseract",str(prefix.with_suffix('.jpg')),"stdout"],timeout=60).decode(errors="replace").strip()
                except UserError:pass
        if len(pages)<total:warnings.append(t("PDF de {total} páginas. Se han procesado las páginas {pages}; no es un resumen del documento completo.",total=total,pages=','.join(map(str,pages))))
        missing=[p for p in pages if len(texts[p])<40 and p not in visual]
        if missing:warnings.append(t("Hay páginas sin texto extraíble y sin captura visual: {pages}. Selecciona un rango menor para analizarlas.",pages=", ".join(map(str,missing))))
        text="\n\n".join(f"[Página {p}]\n{texts[p] or 'Página sin texto extraíble; consultar la captura visual cuando esté disponible.'}" for p in pages)
        if len(text)>150000:warnings.append(t("El texto supera 150.000 caracteres; se ha limitado la captura. Divide el PDF en rangos para estudiar el resto."))
        c=self.app.stage({"kind":"pdf","url":url,"title":title,"text":text[:150000],"images":images,"warnings":warnings},allow_local=True)
        stored=self.app.load(c["id"]);stored["media"]={"type":"pdf","total_pages":total,"pages":pages,"visual_pages":sorted(visual),"method":n("Texto PDF + páginas renderizadas; OCR local cuando hace falta")};self.app.store(stored)
        return self.app.public(stored)

    def transcript_capture(self,segments,title,url,method,images=None,metadata=None,chapters=None,author=None):
        lines=[];pending=list(chapters or [])
        for segment in segments:
            # [FLOW] Each chapter title goes right before its first line of speech.
            while pending and pending[0]['start']<=segment['start']:
                chapter=pending.pop(0);lines.append(f"[{n('Capítulo')} {stamp(chapter['start'])}] {chapter['title']}")
            lines.append(f"[{stamp(segment['start'])}] {segment['text']}")
        text="\n".join(lines)
        warnings=[]
        if len(text)>MAX_TRANSCRIPT:warnings.append(t("La transcripción supera el límite de texto; se conservan los primeros {limit} caracteres. Divide el vídeo para procesar el resto.",limit=f"{MAX_TRANSCRIPT:,}".replace(",",".")))
        c=self.app.stage({"kind":"video","url":url,"title":title,"author":author or "","text":text[:150000],"images":images or [],"warnings":warnings},allow_local=True)
        # [DATA] stage() bounds ordinary captures; a long conversation is read later by stretches.
        stored=self.app.load(c["id"]);stored["text"]=text[:MAX_TRANSCRIPT];stored["media"]={"type":"video","method":method,**(metadata or {})}
        if chapters:stored["media"]["chapters"]=chapters
        self.app.store(stored)
        return self.app.public(stored)

    def audio(self,path,title,url,chapters=None,author=None):
        self.app.progress({'stage':'inspect','message':t('Comprobando duración y pista de audio…')})
        info=json.loads(self.run(["ffprobe","-v","error","-show_format","-show_streams","-of","json",str(path)]))
        duration=float(info.get("format",{}).get("duration") or 0)
        if duration>self.app.config()["video_minutes"]*60:raise UserError("El vídeo supera la duración configurada. Importa un fragmento o aumenta el límite.")
        if not any(s.get("codec_type")=="audio" for s in info.get("streams",[])):raise UserError("El archivo no tiene una pista de audio para transcribir.")
        venv=media_venv(self.app)
        python=venv/("Scripts/python.exe" if os.name=="nt" else "bin/python")
        if not python.exists():raise UserError("Falta el motor de transcripción local. Ejecuta anaco-ob install-media.")
        digest=hashlib.sha256()
        with path.open('rb') as stream:
            while chunk:=stream.read(1048576):self.app.check_cancel();digest.update(chunk)
        key=hashlib.sha256((digest.hexdigest()+self.app.config()['asr_model']+'fw1.2.1-segments-v1').encode()).hexdigest()
        checkpoint=self.app.state/'transcripts'/(key+'.json')
        result=run_progress([str(python),str(Path(__file__).with_name("transcribe.py")),str(path),"--model",self.app.config()["asr_model"],"--cache",str(venv/"models"),'--progress','--checkpoint',str(checkpoint)],self.app.progress,timeout=max(1800,int(duration)),check=self.app.check_cancel)
        if not result["segments"]:raise UserError("No se ha detectado voz en el archivo.")
        images=[]
        if any(s.get("codec_type")=="video" for s in info.get("streams",[])):
            self.app.progress({'stage':'frames','message':t('Transcripción terminada. Extrayendo fotogramas…')})
            for n,second in enumerate([duration*.15,duration*.5,duration*.85][:self.app.config()["video_frames"]]):
                output=path.parent/f"frame-{n}.jpg"
                try:
                    self.run(["ffmpeg","-v","error","-y","-ss",str(second),"-i",str(path),"-frames:v","1","-vf","scale=1280:-2",str(output)])
                    if output.exists():images.append({"data":base64.b64encode(output.read_bytes()).decode(),"alt":n("Fotograma en {time}",time=stamp(second)),"timestamp":second})
                except UserError:self.app.check_cancel()
        return self.transcript_capture(result["segments"],title,url,n("Transcripción local con Whisper {model}",model=self.app.config()["asr_model"]),images,{"duration_seconds":duration,"language":result.get("language"),"coverage":n("Audio del archivo completo")},chapters,author)

    def video_url(self,message):
        url=normalized_url(message.get("url",""));directory=self.app.state/"uploads"/uuid.uuid4().hex;directory.mkdir(parents=True,mode=0o700)
        self.app.progress({'stage':'subtitles','message':t('Buscando subtítulos y audio en la plataforma…')})
        network=['--socket-timeout','20','--retries','2','--extractor-retries','2']
        meta=json.loads(self.run(["yt-dlp","--ignore-config","--no-playlist",*network,"--skip-download","--dump-single-json",url],timeout=180))
        if meta.get("is_live"):raise UserError("Para directos, importa una grabación terminada.")
        if (meta.get("duration") or 0)>self.app.config()["video_minutes"]*60:raise UserError("El vídeo supera la duración configurada.")
        title=meta.get("title") or "Vídeo";author=clean(meta.get("channel") or meta.get("uploader"),200).strip()
        chapters=sorted(({"start":int(v["start_time"]),"title":clean(v.get("title"),200).replace("\n"," ").strip()} for v in meta.get("chapters") or []
                         if isinstance(v,dict) and isinstance(v.get("start_time"),(int,float)) and clean(v.get("title"),200).strip()),key=lambda v:v["start"])
        for kind,key in [(n("Subtítulos de la plataforma"),"subtitles"),(n("Subtítulos automáticos de la plataforma"),"automatic_captions")]:
            languages=meta.get(key) or {}
            for language in sorted(languages,key=lambda lang:(not lang.startswith("es"),not lang.startswith("en"),lang)):
                entry=next((e for e in languages[language] if e.get("ext") in ("vtt","srt")),None)
                if entry:
                    self.app.progress({'stage':'subtitles','message':t('Recuperando los subtítulos de la plataforma…')})
                    request=Request(normalized_url(entry["url"]),headers={"User-Agent":"Mozilla/5.0"})
                    try:
                        with urlopen(request,timeout=30) as response:content=response.read(5_000_001)
                        if len(content)>5_000_000:raise UserError("Los subtítulos son demasiado grandes.")
                        return self.transcript_capture(subtitles(content.decode(errors="replace")),title,url,kind,metadata={"language":language,"duration_seconds":meta.get("duration"),"coverage":n("Subtítulos disponibles en la plataforma")},chapters=chapters,author=author)
                    except (OSError,UserError):continue
        self.app.progress({'stage':'download','message':t('Sin subtítulos accesibles. Descargando audio para transcribir…')})
        self.run(["yt-dlp","--ignore-config","--no-playlist",*network,"--max-filesize","100M","-f","bestaudio[filesize<95M]/bestaudio[filesize_approx<95M]/worstaudio/bestaudio/best","-o",str(directory/"source.%(ext)s"),url],timeout=600)
        files=[p for p in directory.glob("source.*") if p.suffix not in (".part",".ytdl")]
        if not files or files[0].stat().st_size>MAX_FILE:raise UserError("No se ha podido descargar un audio compatible de hasta 100 MB. Importa el archivo desde la plataforma.")
        return self.audio(files[0],title,url,chapters,author)

