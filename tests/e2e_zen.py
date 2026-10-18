#!/usr/bin/env python3
"""Real Zen + installed WebExtension + native host + review UI + temporary vault.

Only the test copy receives localhost host permissions, allowing WebDriver to
exercise capture without clicking a browser toolbar. Production uses activeTab.
"""
import argparse
import functools
import http.server
import json
import os
import signal
import shlex
import re
from pathlib import Path
import struct
import time
import subprocess
import sys
import threading
import tempfile
import shutil
import zipfile
import zlib

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "native"))
from core import App


def fixture_png():
    def chunk(kind, value):
        return struct.pack('!I', len(value)) + kind + value + struct.pack('!I', zlib.crc32(kind + value))
    width, height = 240, 160
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            block = (15 < x < 75 or 90 < x < 150 or 165 < x < 225) and 50 < y < 110
            row.extend((166, 139, 250) if block else (35, 33, 43))
        rows.append(b'\0' + row)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!2I5B', width, height, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b'')


def main():
    signal.signal(signal.SIGTERM,lambda *_:sys.exit(143))
    parser = argparse.ArgumentParser()
    parser.add_argument("--ai", action="store_true")
    parser.add_argument('--editorial',action='store_true',help='Review and save an editable linked collection with a deterministic model fixture')
    parser.add_argument('--session-video',action='store_true',help='Video, captions and HLS requiring the actual player referrer and session')
    parser.add_argument('--quality',action='store_true',help='Narrow sidebar, full image gallery, selection limit and visible progress')
    parser.add_argument('--workflow',action='store_true',help='Scoped revisions, merge, amendments, cancellation/resume and automatic review')
    parser.add_argument('--windows',action='store_true',help='New browser windows do not inherit the capture panel or steal focus')
    parser.add_argument("--book-ai", action="store_true", help="Use a deterministic CLI fixture to verify all 55 reading pages and native progress")
    parser.add_argument("--book-images", action="store_true", help="Read all 55 pages using real local OCR")
    parser.add_argument("--book", action="store_true", help="Extract a complete 55-page book and verify a stable panel")
    parser.add_argument("--reader", action="store_true", help="Capture an embedded HTML book with redirects, canvas, SVG and background images")
    parser.add_argument("--copy-error", action="store_true", help="Verify the real clipboard and copy fallback")
    parser.add_argument("--manual-import", action="store_true", help="Check the separate manual importer and its review")
    parser.add_argument("--detection", action="store_true", help="Exercise active-tab detection and nested authenticated course resources")
    parser.add_argument("--options", action="store_true", help="Exercise vault discovery and manual configuration in Options")
    parser.add_argument('--profile',action='store_true',help='Vault without profile: scan in Options, confirm, save a note with the vault frontmatter and detect a moved guide')
    parser.add_argument('--embeds-live',action='store_true',help='Network: capture the real Codrops spotlight with its tweets, pens and clips')
    parser.add_argument('--embeds',action='store_true',help='Embedded posts, CodePen and silent clips in a web article; course mode keeps the previous detection')
    parser.add_argument('--code',action='store_true',help='Capture cached real Codrops HTML and verify literal code and note organization')
    parser.add_argument('--review-menu',action='store_true',help='Review assistant menu, per-topic connections, manual close and sidebar save')
    parser.add_argument('--split-review',action='store_true',help='Review a split suggestion, discard it, then accept and save without losing edits')
    parser.add_argument("--fresh-permissions", action="store_true", help="Exercise a new optional image host through the real permission prompt")
    parser.add_argument("--media",action="store_true",help="Exercise native PDF viewer, course iframe, subtitles and local imports")
    args = parser.parse_args()
    args.book = args.book or args.book_images
    out = ROOT / ".test-artifacts" / ("zen-book-images" if args.book_images else "zen-book" if args.book else "zen-reader" if args.reader else "zen-copy-error" if args.copy_error else "zen-import" if args.manual_import else "zen-detection" if args.detection else "zen-options" if args.options else "zen-media" if args.media else "zen-permissions" if args.fresh_permissions else "zen-ai" if args.ai else "zen")
    out.mkdir(parents=True, exist_ok=True)
    if args.editorial:out=ROOT/'.test-artifacts/zen-editorial';out.mkdir(parents=True,exist_ok=True)
    if args.session_video:out=ROOT/'.test-artifacts/zen-session-video';out.mkdir(parents=True,exist_ok=True)
    if args.quality:out=ROOT/'.test-artifacts/zen-quality';out.mkdir(parents=True,exist_ok=True)
    if args.workflow:out=ROOT/'.test-artifacts/zen-workflow';out.mkdir(parents=True,exist_ok=True)
    if args.windows:out=ROOT/'.test-artifacts/zen-windows';out.mkdir(parents=True,exist_ok=True)
    if args.code:out=ROOT/'.test-artifacts/zen-code';out.mkdir(parents=True,exist_ok=True)
    args.embeds=args.embeds or args.embeds_live
    if args.embeds:out=ROOT/'.test-artifacts'/('zen-embeds-live' if args.embeds_live else 'zen-embeds');out.mkdir(parents=True,exist_ok=True)
    if args.review_menu:out=ROOT/'.test-artifacts/zen-review-menu';out.mkdir(parents=True,exist_ok=True)
    if args.profile:out=ROOT/'.test-artifacts/zen-profile';out.mkdir(parents=True,exist_ok=True)
    if args.split_review:out=ROOT/'.test-artifacts/zen-split-review';out.mkdir(parents=True,exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="run-",dir=out))
    vault = run_dir / "Vault"
    for name in ("02_Cerebro/Modelos_Mentales", "02_Cerebro/Tech_&_Codigo", "07_Clases/01_Curso/01_Tema", "99_Recursos"):
        (vault / name).mkdir(parents=True, exist_ok=True)
    (vault / "02_Cerebro/Modelos_Mentales/recuperacion_activa.md").write_text("# Recuperación activa\n\nIntentar recordar sin mirar fortalece la memoria. Las pruebas sin apuntes ayudan a detectar lagunas y corregir errores.")
    (vault / "02_Cerebro/Tech_&_Codigo/recuperacion_paquetes.md").write_text("# Recuperación de paquetes\n\nLa recuperación de paquetes perdidos utiliza retransmisión en redes de ordenadores. Los routers conectan equipos.")
    app = App(run_dir / "state")
    app.set_config({"vault":str(vault), "provider":"codex" if args.ai else "manual",'note_structure':'linked' if args.editorial or args.workflow or args.review_menu else 'single'})
    if args.profile:
        # A reduced copy of the reorganized second_brain, with no profile yet.
        sys.path.insert(0,str(ROOT/'tests'))
        from test_vault_scan import second_brain
        vault=second_brain(run_dir);app.set_config({"vault":str(vault),"provider":"manual"})
    else:
        from vault_profile import install
        install(app, json.loads((ROOT/'tests/fixtures/profile-classic.json').read_text()), '99_Recursos/anaco/perfil.json')
    app.db.close()
    (ROOT / "tests/fixtures/diagram.png").write_bytes(fixture_png())
    if args.media or args.detection:
        sys.path.insert(0,str(ROOT/'tests'))
        from media_fixtures import make_pdf
        pdf=make_pdf(run_dir/'fixtures');shutil.copyfile(pdf,ROOT/'tests/fixtures/lesson.pdf')
        (ROOT/'tests/fixtures/lesson.vtt').write_text('WEBVTT\n\n00:00.000 --> 00:03.000\nIAM controla el acceso a recursos.\n\n00:04.000 --> 00:07.000\nUna política aplica el privilegio mínimo.\n')
        (ROOT/'tests/fixtures/course-frame.html').write_text('<html><title>Lección incrustada</title><main><h1>Lección de IAM</h1><video controls src="lesson.mp4"><track kind="subtitles" src="lesson.vtt" srclang="es" label="Español"></video></main></html>')
        (ROOT/'tests/fixtures/course.html').write_text('<html><title>Curso privado simulado</title><main><a class="file_download_btn" href="lesson.pdf">Material PDF</a><iframe title="Lección del curso" src="course-frame.html"></iframe></main></html>')
        audio=ROOT/'.test-artifacts/jfk.flac'
        if audio.exists():
            subprocess.run(['pdftoppm','-f','2','-l','2','-scale-to','640','-jpeg','-singlefile',str(pdf),str(run_dir/'slide')],check=True)
            subprocess.run(['ffmpeg','-v','error','-y','-loop','1','-i',str(run_dir/'slide.jpg'),'-i',str(audio),'-t','6','-vf','scale=640:-2','-c:v','libx264','-preset','ultrafast','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(ROOT/'tests/fixtures/lesson.mp4')],check=True)
    manifest_paths = [Path.home() / ".mozilla/native-messaging-hosts/org.samuh.anaco_ob.json", Path.home() / ".config/zen/native-messaging-hosts/org.samuh.anaco_ob.json"]
    backups = {p: p.read_bytes() if p.exists() else None for p in manifest_paths}
    driver = None
    server = None
    try:
        subprocess.run([sys.executable, str(ROOT / "scripts/install.py"), "--state", str(run_dir / "state"), "--vault", str(vault)],check=True)
        if args.options:
            registry = run_dir / 'xdg/obsidian/obsidian.json'
            registry.parent.mkdir(parents=True)
            registry.write_text(json.dumps({'vaults': {'fixture': {'path': str(vault)}}}))
            launcher = run_dir / 'state/native-host'
            launcher.write_text(launcher.read_text().replace('#!/bin/sh\n', '#!/bin/sh\nexport XDG_CONFIG_HOME=' + shlex.quote(str(run_dir / 'xdg')) + '\n', 1))
        extension = out / "test-extension.zip"
        with zipfile.ZipFile(extension,"w",zipfile.ZIP_DEFLATED) as archive:
            for p in (ROOT / "extension").rglob("*"):
                if not p.is_file():continue
                relative=p.relative_to(ROOT/"extension").as_posix()
                if p.name == "manifest.json":
                    manifest=json.loads(p.read_text());manifest["permissions"].append("http://127.0.0.1/*")
                    if args.copy_error:manifest["permissions"].append("clipboardRead")
                    # Pre-granted so the selection click does not open a permission prompt.
                    if args.embeds:manifest["permissions"]+=["https://codepen.io/*","https://cdpn.io/*"]+(["https://tympanus.net/*"] if args.embeds_live else [])
                    archive.writestr(relative,json.dumps(manifest))
                else:archive.write(p,relative)
        if args.book_ai or args.editorial or args.workflow or args.split_review or args.review_menu:
            fake=run_dir/'fake_book_cli.py'
            shutil.copyfile(ROOT/('tests/fake_editorial_cli.py' if args.editorial or args.workflow or args.split_review or args.review_menu else 'tests/fake_book_cli.py'),fake);fake.chmod(0o700)
            config_path=run_dir/'state/config.json'
            config=json.loads(config_path.read_text());config['codex']=str(fake);config_path.write_text(json.dumps(config))
        session_requests=[]
        class CourseHandler(http.server.SimpleHTTPRequestHandler):
            def guess_type(self,path):
                value=super().guess_type(path)
                return value+'; charset=utf-8' if value.startswith('text/') else value
            def end_headers(self):
                self.send_header('Set-Cookie','zen_course=test; Path=/; SameSite=Lax')
                super().end_headers()
            def do_HEAD(self):
                if self.path.split('?')[0]=='/courses/1/files/22/download':
                    self.send_response(200);self.send_header('Content-Type','application/pdf');self.end_headers();return
                super().do_HEAD()
            def do_GET(self):
                if args.code and self.path=='/edge-code.html':
                    page=b'<!doctype html><meta charset="utf-8"><article><h1>Code fidelity</h1><p>A reference example with source code, whitespace and template delimiters. It explains a literal string and a second statement for future consultation.</p><pre class="language-js"><code>const text = "```";\n\n\nconst y = 2;</code></pre><p>Inline: <code>a &lt; b &amp;&amp; c</code>.</p></article>'
                    self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(page);return
                if args.code and self.path=='/code-article.html':
                    cached=json.loads((ROOT/'.test-artifacts/codrops-code/source.json').read_text())
                    html=re.sub(r'<(?:script|style)\b[^>]*>.*?</(?:script|style)>','',cached['html'],flags=re.S|re.I)
                    html=re.sub(r'<(?:img|source)\b[^>]*>','',html,flags=re.I)
                    html=re.sub(r'<(?:video|iframe)\b[^>]*>.*?</(?:video|iframe)>','',html,flags=re.S|re.I)
                    page=('<!doctype html><html><head><meta charset="utf-8"><title>'+cached['title']+'</title></head><body>'+html+'</body></html>').encode()
                    self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(page);return
                if (args.session_video or args.workflow) and self.path.startswith('/session-media/'):
                    from urllib.parse import urlparse
                    path=self.path.split('?')[0];referrer=urlparse(self.headers.get('Referer',''))
                    authorized=referrer.path=='/session-player.html' and referrer.netloc==self.headers.get('Host') and 'zen_course=test' in self.headers.get('Cookie','') and not path.endswith('denied.mp4')
                    session_requests.append({'path':path,'player_referrer':referrer.path=='/session-player.html','session': 'zen_course=test' in self.headers.get('Cookie',''),'status':200 if authorized else 403})
                    if not authorized:self.send_error(403,'Player session and referrer required');return
                    if path.endswith('captions.vtt'):data=b'WEBVTT\n\n00:00.000 --> 00:04.000\nIAM controla el acceso a recursos con permisos temporales.\n';mime='text/vtt'
                    elif path.endswith('video.mp4'):data=(ROOT/'tests/fixtures/lesson.mp4').read_bytes();mime='video/mp4'
                    elif path.endswith('master.m3u8'):data=b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=100000\nhls/stream.m3u8\n';mime='application/vnd.apple.mpegurl'
                    else:
                        file=run_dir/'session-hls'/Path(path).name;data=file.read_bytes();mime='application/vnd.apple.mpegurl' if file.suffix=='.m3u8' else 'video/mp2t'
                    self.send_response(200);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
                if self.path.split('?')[0]=='/reader-launch.html':
                    self.send_response(302);self.send_header('Location','/reader-wrapper.html');self.end_headers();return
                if self.path.split('?')[0]=='/courses/1/files/22/download':
                    if 'zen_course=test' not in self.headers.get('Cookie',''):
                        self.send_error(403,'Session required');return
                    self.send_response(200);self.send_header('Content-Type','application/pdf');self.end_headers();self.wfile.write((ROOT/'tests/fixtures/lesson.pdf').read_bytes());return
                if (args.media or args.detection) and self.path.split('?')[0].endswith(('.pdf','.vtt','.m3u8','.ts')) and 'zen_course=test' not in self.headers.get('Cookie',''):
                    self.send_error(403,'Session required');return
                super().do_GET()
        handler=functools.partial(CourseHandler,directory=str(ROOT / "tests/fixtures"))
        server=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        url=f"http://127.0.0.1:{server.server_port}/article.html"
        if args.quality:
            (ROOT/'tests/fixtures/gallery.html').write_text('<!doctype html><meta charset="utf-8"><title>Galería para estudiar diseño</title><article><h1>Galería para estudiar diseño</h1><p>Un artículo con diagramas diferentes para comprobar que todas las figuras se pueden revisar antes de elegir cuáles conservar en los apuntes.</p>'+''.join(f'<figure><img src="diagram.png?n={n}" width="240" height="160" alt="Diagrama {n}: conceptos y conexiones"><figcaption>Explicación original de la figura {n}.</figcaption></figure>' for n in range(1,25))+'</article>')
        if args.session_video or args.workflow:
            hls=run_dir/'session-hls';hls.mkdir()
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(ROOT/'tests/fixtures/lesson.mp4'),'-c','copy','-hls_time','2','-hls_playlist_type','vod',str(hls/'stream.m3u8')],check=True)
            (ROOT/'tests/fixtures/session-course.html').write_text('<html><title>Curso con vídeo protegido</title><iframe id="player" title="Reproductor privado"></iframe><script>document.getElementById("player").src="session-player.html"+location.search;</script></html>')
            (ROOT/'tests/fixtures/session-player.html').write_text('''<html><title>Reproductor privado</title><video controls id="video"></video><script>
              const mode=new URL(location.href).searchParams.get('mode'),v=document.getElementById('video');
              v.src=mode==='blocked'?'/session-media/denied.mp4?signature=DO_NOT_COPY':mode==='hls'?'/session-media/master.m3u8':'/session-media/video.mp4';
              if(mode==='captions'){const track=document.createElement('track');track.kind='subtitles';track.src='/session-media/captions.vtt';track.srclang='es';v.append(track);}
            </script></html>''')
        if args.detection:
            fixtures=ROOT/'tests/fixtures'
            (fixtures/'session.html').write_text('<html><title>Sesión del reproductor</title><main>Sesión de prueba iniciada.</main></html>')
            (fixtures/'empty.html').write_text('<html><title>Vacío</title><main><h1>Sin contenido</h1></main></html>')
            (fixtures/'blocked-video.html').write_text('<html><title>Reproductor bloqueado</title><main><video src="blob:inaccessible" controls></video></main></html>')
            (fixtures/'nested-course.html').write_text(f'<html><title>Curso anidado</title><main><iframe src="http://localhost:{server.server_port}/nested-wrapper.html" title="Lección del curso"></iframe></main></html>')
            (fixtures/'nested-wrapper.html').write_text('<html><title>Visor del curso</title><iframe src="course-frame.html" title="Vídeo de la unidad"></iframe></html>')
            (fixtures/'dynamic-video.html').write_text("""<html><title>Vídeo dinámico</title><main><video id="player" controls></video></main><script>
              setTimeout(async()=>{await fetch('hls/stream.m3u8');document.getElementById('player').src=URL.createObjectURL(new Blob(['media'],{type:'video/mp4'}));},1500);
            </script></html>""")
            hls=fixtures/'hls';hls.mkdir(exist_ok=True)
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(fixtures/'lesson.mp4'),'-c','copy','-hls_time','2','-hls_playlist_type','vod',str(hls/'stream.m3u8')],check=True)

        if args.reader:
            fixtures=ROOT/'tests/fixtures'
            sys.path.insert(0,str(ROOT/'tests'))
            from media_fixtures import make_pdf
            original=make_pdf(run_dir/'book-pdf')
            shutil.copyfile(original,fixtures/'reader-original.pdf')
            (fixtures/'reader-pdf.html').write_text('<html><title>Visor de libro con PDF</title><body><div class="pdfViewer"><canvas width="400" height="300"></canvas></div><script>fetch("reader-original.pdf").then(r=>r.arrayBuffer()).then(()=>document.body.dataset.ready="yes");</script></body></html>')
            (fixtures/'reader-many.html').write_text('<html><title>Libro largo</title><main class="book-content">'+''.join('<canvas width="200" height="120"></canvas>' for _ in range(10))+'<script>for(const canvas of document.querySelectorAll("canvas")){const c=canvas.getContext("2d");c.fillStyle="purple";c.fillRect(0,0,200,120);c.fillStyle="white";c.fillText("Página de prueba",20,60);}</script></main></html>')

            (fixtures/'reader-shell.html').write_text(f'<html><title>Libro del curso</title><main><iframe title="Lector" src="http://localhost:{server.server_port}/reader-launch.html" width="850" height="850"></iframe></main></html>')
            (fixtures/'reader-wrapper.html').write_text('<html><title>Visor del curso</title><iframe src="reader-book.html" width="800" height="800"></iframe></html>')
            (fixtures/'reader-book.html').write_text("""<!doctype html><html><head><meta charset="utf-8"><title>Página de IAM</title></head><body><main class="book-content">
              <h1>Identidades y permisos</h1><p>Una identidad solicita acceso a un recurso. Las políticas definen las acciones permitidas y los recursos disponibles para cada identidad. Esta página del libro explica el acceso de usuarios y roles a un bucket de almacenamiento.</p>
              <div class="page" id="css-page" style="width:400px;height:200px;background-image:url(diagram.png)"></div>
              <canvas id="canvas-page" width="500" height="220"></canvas>
              <svg xmlns="http://www.w3.org/2000/svg" width="500" height="180"><rect width="500" height="180" fill="#34234f"/><rect x="20" y="40" width="140" height="70" fill="#967acc"/><text x="30" y="80" fill="white">Identidad</text><text x="200" y="80" fill="white">→ Política → S3</text></svg>
              <section class="page" style="margin-top:1400px"><p>SEGUNDA PÁGINA CARGADA FUERA DE LA PANTALLA. Las políticas conceden acceso únicamente a las acciones y recursos definidos. El texto de esta página también debe recuperarse.</p></section><div class="page" style="display:none"><p>PÁGINA OCULTA QUE NO SE DEBE CAPTURAR</p><img src="diagram.png"></div>
              <script>const c=document.querySelector('canvas').getContext('2d');c.fillStyle='#3b4252';c.fillRect(0,0,500,220);c.fillStyle='white';c.font='24px sans-serif';c.fillText('Identidad → Política → Recurso',20,110);</script>
            </main></body></html>""")
        if args.book:
            pages=''.join(f'<section class="page" data-page-number="{n}" style="width:650px;min-height:420px"><h2>Page {n}</h2><p>UNIQUE PAGE {n}. Cloud permissions define the actions that an identity can perform on a resource. Use least privilege and audit access regularly. This is the complete text of training page {n}.</p><canvas width="600" height="220" data-number="{n}"></canvas></section>' for n in range(1,56))
            if args.book_images:pages=''.join(f'<section class="page" data-page-number="{n}" style="width:650px;min-height:420px"><canvas width="600" height="220" data-number="{n}"></canvas></section>' for n in range(1,56))
            (ROOT/'tests/fixtures/book-55.html').write_text('<!doctype html><html><head><meta charset="utf-8"><title>Cloud book: 55 pages</title></head><body><main class="book-content">'+pages+'<script>for(const canvas of document.querySelectorAll("canvas")){const c=canvas.getContext("2d");c.fillStyle="#34234f";c.fillRect(0,0,600,220);c.fillStyle="white";c.font="28px sans-serif";c.fillText("UNIQUE PAGE "+canvas.dataset.number,20,75);c.fillText("Identity - Policy - Resource",20,145);}</script></main></body></html>')
        options=Options();options.binary_location="/opt/zen-browser-bin/zen";options.add_argument("-headless")
        options.set_preference("zen.welcome-screen.seen",True)
        options.set_preference("browser.shell.checkDefaultBrowser",False)
        driver=webdriver.Firefox(options=options,service=Service(executable_path=str(ROOT / ".test-artifacts/bin/geckodriver"),service_args=["--allow-system-access"],log_output=str(out/"geckodriver.log")))
        driver.set_window_size(1100,1100)
        addon=driver.install_addon(str(extension),temporary=True)
        driver.set_context("chrome")
        uuids=json.loads(driver.execute_script('return Services.prefs.getStringPref("extensions.webextensions.uuids")'))
        driver.set_context("content")
        panel=f"moz-extension://{uuids[addon]}/panel.html"
        driver.get(panel)
        panel_handle=driver.current_window_handle
        wait=WebDriverWait(driver,30)
        wait.until(lambda d:"CONECTADO" in d.find_element(By.ID,"connection").text)
        driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.set({autoReview:false}).then(done);')
        def field(identifier):
            element=driver.find_element(By.ID,identifier)
            driver.execute_script('let e=arguments[0];for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;',element)
            return element
        def message(value, timeout=30):
            driver.set_script_timeout(timeout)
            answer=driver.execute_async_script('const done=arguments[arguments.length-1]; browser.runtime.sendMessage(arguments[0]).then(result=>done({ok:true,result}),error=>done({ok:false,error:error.message}));',value)
            assert answer["ok"],answer
            return answer["result"]
        if args.windows:
            original=driver.execute_async_script('const done=arguments[arguments.length-1];browser.windows.getCurrent().then(done);')
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.runtime.getBackgroundPage().then(bg=>{bg.testSidebarPolicy=[];const previous=bg.allowSidebar;bg.allowSidebar=async id=>{const allowed=await previous(id);bg.testSidebarPolicy.push({id,allowed});return allowed;};done(true);});')
            def sidebar_chrome(show,owner=None):
                driver.set_context('chrome')
                if show:
                    result=driver.execute_async_script('const done=arguments[arguments.length-1];const windows=[...Services.wm.getEnumerator("navigator:browser")];const owner=windows.find(w=>w.docShell.outerWindowID===arguments[1]);if(!owner){done({error:"window not found",ids:windows.map(w=>w.docShell.outerWindowID)});return;}const controller=owner.SidebarController;const sidebars=controller.sidebars||controller._sidebars;const entry=[...sidebars.entries()].find(([id,value])=>id.includes("second-brain")||value.extensionId===arguments[0]);if(!entry){done({error:"sidebar not found",keys:[...sidebars.keys()]});return;}controller.show(entry[0]).then(()=>done({id:entry[0],open:controller.isOpen}));',addon,owner or original['id'])
                    assert not result.get('error'),result
                    assert result['open'],result
                else:driver.execute_script('const owner=[...Services.wm.getEnumerator("navigator:browser")].find(w=>w.docShell.outerWindowID===arguments[0]);owner.SidebarController.hide();',owner or original['id'])
                driver.set_context('content')
            def is_open(window_id):
                return driver.execute_async_script('const done=arguments[arguments.length-1];browser.sidebarAction.isOpen({windowId:arguments[0]}).then(done);',window_id)
            sidebar_chrome(True);wait.until(lambda d:is_open(original['id']))
            assert is_open(original['id'])
            handles=set(driver.window_handles)
            second=driver.execute_async_script('const done=arguments[arguments.length-1];browser.windows.create({url:arguments[0],focused:true,type:"normal"}).then(done);',url)
            wait.until(lambda d:d.execute_async_script('const done=arguments[arguments.length-1];browser.runtime.getBackgroundPage().then(bg=>done(bg.testSidebarPolicy.some(v=>v.id===arguments[0]&&!v.allowed)));',second['id']))
            wait.until(lambda d:not is_open(second['id']))
            assert is_open(original['id'])
            new_handle=wait.until(lambda d:next(iter(set(d.window_handles)-handles),None));driver.switch_to.window(new_handle)
            # An intentional open in the new window remains available.
            sidebar_chrome(True,second['id'])
            driver.switch_to.window(panel_handle)
            wait.until(lambda d:d.execute_async_script('const done=arguments[arguments.length-1];browser.runtime.getBackgroundPage().then(bg=>done(bg.testSidebarPolicy.some(v=>v.id===arguments[0]&&v.allowed)));',second['id']))
            # Closing a panel and opening another ordinary tab never reopens it.
            sidebar_chrome(False)
            tab=driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.create({url:arguments[0],windowId:arguments[1],active:true}).then(done);',url,original['id'])
            driver.execute_async_script('const done=arguments[arguments.length-1];setTimeout(done,500);')
            assert not is_open(original['id'])
            c=message({'type':'native','message':{'action':'capture','capture':{'kind':'article','url':url,'title':'Window focus fixture','text':'A synthetic article used only to check that completing a note does not activate a different browser window.'}}})
            message({'type':'native','message':{'action':'draft','id':c['id'],'provider':'manual'}})
            focus=driver.execute_async_script('''const done=arguments[arguments.length-1],id=arguments[0],sourceTab=arguments[1],away=arguments[2];
              browser.runtime.getBackgroundPage().then(async bg=>{const source={tabId:sourceTab.id,windowId:sourceTab.windowId,url:sourceTab.url};await browser.windows.update(away,{focused:true});const before=await browser.windows.getLastFocused();const review=await bg.openReview(id,{automatic:true,source});const after=await browser.windows.getLastFocused();const result=await browser.tabs.get(review.tabId);done({before:before.id,after:after.id,windowId:result.windowId,active:result.active});}).catch(e=>done({error:e.message}));''',c['id'],tab,second['id'])
            assert focus=={'before':second['id'],'after':second['id'],'windowId':original['id'],'active':False},focus
            report={'passed':True,'browser':driver.capabilities['browserVersion'],'inherited_sidebar_closed':True,'original_sidebar_preserved':True,'explicit_open_still_works':True,'new_tab_keeps_closed_panel_closed':True,'review_stays_in_source_window':True,'review_does_not_steal_focus':True,'window_focus':focus}
            (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2));return
        if args.copy_error:
            driver.set_window_size(480,900)
            sample='El visor del curso no permite recuperar los subtítulos (HTTP 403).'
            diagnostic='{"framesRead": 3, "framesBlocked": 1}'
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.set({operationError:arguments[0],pageContext:{status:"ready",url:"https://course.example/"}}).then(done);',sample)
            wait.until(lambda d:d.find_element(By.ID,'error').text==sample)
            driver.execute_script('document.getElementById("diagnostic").hidden=false;document.getElementById("detectionReport").textContent=arguments[0];',diagnostic)
            driver.find_element(By.ID,'copyError').click()
            wait.until(lambda d:'Copiado' in d.find_element(By.ID,'copyError').text)
            copied=driver.execute_async_script('const done=arguments[arguments.length-1];navigator.clipboard.readText().then(done);')
            assert sample in copied and diagnostic in copied and 'Anaco '+json.loads((ROOT/'extension/manifest.json').read_text())['version'] in copied,copied
            assert driver.find_element(By.ID,'error').text==sample
            driver.save_screenshot(str(out/'copy-error.png'))
            driver.find_element(By.CSS_SELECTOR,'#diagnostic summary').click()
            driver.find_element(By.ID,'copyDiagnostic').click()
            wait.until(lambda d:'Copiado' in d.find_element(By.ID,'copyDiagnostic').text)
            # An unavailable clipboard must not replace the original error.
            driver.execute_script('Object.defineProperty(navigator,"clipboard",{configurable:true,value:{writeText:async()=>{throw new Error("blocked");}}});')
            driver.find_element(By.ID,'copyError').click()
            wait.until(lambda d:d.find_element(By.ID,'copyFallback').is_displayed())
            fallback=driver.find_element(By.ID,'copyFallback')
            assert sample in fallback.get_attribute('value')
            assert driver.execute_script('const e=document.getElementById("copyFallback");return document.activeElement===e&&e.selectionStart===0&&e.selectionEnd===e.value.length;')
            assert driver.find_element(By.ID,'error').text==sample
            driver.execute_script('document.getElementById("error").hidden=true;')
            assert not driver.find_element(By.ID,'copyError').is_displayed()
            report={'passed':True,'real_clipboard':True,'error_and_diagnostic':True,'diagnostic_button':True,'original_error_preserved':True,'fallback_selected':True}
            (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
            return
        if args.options:
            options_url = panel.replace('panel.html', 'options.html')
            driver.get(options_url)
            wait.until(lambda d: 'Servicio conectado' in d.find_element(By.ID, 'message').text)
            assert driver.find_element(By.ID, 'vault').get_attribute('value') == str(vault)
            assert Select(driver.find_element(By.ID, 'vault_mode')).first_selected_option.get_attribute('value') == 'manual'
            Select(driver.find_element(By.ID, 'vault_mode')).select_by_value('auto')
            wait.until(lambda d: not d.find_element(By.ID, 'detect-vaults').get_attribute('disabled'))
            Select(driver.find_element(By.ID, 'detected-vault')).select_by_value(str(vault))
            assert driver.find_element(By.ID, 'vault').get_attribute('readonly')
            # The real registry may also be listed. All saves stay in our fake vault.
            detected = [o.get_attribute('value') for o in Select(driver.find_element(By.ID, 'detected-vault')).options if o.get_attribute('value')]
            def save_options():
                driver.find_element(By.CSS_SELECTOR, '#settings [type="submit"]').click()
                wait.until(lambda d: 'Opciones guardadas' in d.find_element(By.ID, 'message').text)
            save_options()
            driver.refresh()
            wait.until(lambda d: d.find_element(By.ID, 'vault').get_attribute('value') == str(vault))
            assert Select(driver.find_element(By.ID, 'vault_mode')).first_selected_option.get_attribute('value') == 'auto'
            Select(driver.find_element(By.ID, 'vault_mode')).select_by_value('manual')
            path_input = driver.find_element(By.ID, 'vault')
            path_input.clear(); path_input.send_keys(str(run_dir / 'absent'))
            driver.find_element(By.CSS_SELECTOR, '#settings [type="submit"]').click()
            wait.until(lambda d: 'No encuentro esa carpeta' in d.find_element(By.ID, 'message').text)
            assert message({'type': 'native', 'message': {'action': 'settings'}})['config']['vault'] == str(vault)
            path_input.clear(); path_input.send_keys(str(vault))
            save_options()
            # Simulate a moved vault without requiring any filesystem changes.
            config_path = run_dir / 'state/config.json'
            cfg = json.loads(config_path.read_text())
            cfg['vault'] = str(run_dir / 'moved')
            config_path.write_text(json.dumps(cfg))
            driver.refresh()
            wait.until(lambda d: 'Localiza tu vault' in d.find_element(By.ID, 'message').text)
            assert driver.find_element(By.ID, 'model').get_attribute('value') == cfg['model']
            path_input = driver.find_element(By.ID, 'vault')
            path_input.clear(); path_input.send_keys(str(vault))
            save_options()
            driver.refresh()
            wait.until(lambda d: 'Servicio conectado' in d.find_element(By.ID, 'message').text)
            assert driver.find_element(By.ID, 'vault').get_attribute('value') == str(vault)
            assert not driver.find_element(By.ID, 'vault').get_attribute('readonly')
            # Options opened directly still has a way out; leaving keeps edits
            # locally without configuring the service until Save is clicked.
            pending_model = cfg['model'] + '-unsaved'
            model_input = driver.find_element(By.ID, 'model')
            model_input.clear(); model_input.send_keys(pending_model)
            driver.set_window_size(420, 720)
            driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
            back = driver.find_element(By.ID, 'back-to-capture')
            assert driver.execute_script('const r=arguments[0].getBoundingClientRect();return r.top>=0&&r.bottom<innerHeight', back)
            assert driver.execute_script('return document.documentElement.scrollWidth<=innerWidth')
            driver.save_screenshot(str(out / 'options.png'))
            back.click()
            wait.until(lambda d: d.current_url == panel)
            wait.until(lambda d: 'CONECTADO' in d.find_element(By.ID, 'connection').text)
            assert message({'type': 'native', 'message': {'action': 'settings'}})['config']['model'] == cfg['model']

            # Zen's WebDriver startup tab has extension tab ID -1. Create a
            # normal registered tab to exercise returning to a real source.
            handles = set(driver.window_handles)
            source_tab = driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.create({url:arguments[0],active:true}).then(done);', panel)
            assert source_tab['id'] >= 0
            panel_handle = wait.until(lambda d: next(iter(set(d.window_handles) - handles), None))
            driver.switch_to.window(panel_handle)
            wait.until(lambda d: 'CONECTADO' in d.find_element(By.ID, 'connection').text)

            def open_options_from_panel():
                handles = set(driver.window_handles)
                driver.find_element(By.ID, 'options').click()
                handle = wait.until(lambda d: next(iter(set(d.window_handles) - handles), None))
                driver.switch_to.window(handle)
                wait.until(lambda d: 'Servicio conectado' in d.find_element(By.ID, 'message').text)
                return handle

            options_handle = open_options_from_panel()
            assert driver.find_element(By.ID, 'model').get_attribute('value') == pending_model
            assert 'Cambios sin guardar' in driver.find_element(By.ID, 'options-draft-status').text
            driver.find_element(By.ID, 'back-to-capture').click()
            wait.until(lambda d: options_handle not in d.window_handles)
            driver.switch_to.window(panel_handle)
            assert driver.current_url == panel

            options_handle = open_options_from_panel()
            assert driver.find_element(By.ID, 'model').get_attribute('value') == pending_model
            model_input = driver.find_element(By.ID, 'model')
            model_input.clear(); model_input.send_keys(cfg['model'])
            save_options()
            assert driver.execute_script('return localStorage.getItem("optionsDraft")') is None
            driver.find_element(By.ID, 'back-to-capture').click()
            wait.until(lambda d: options_handle not in d.window_handles)
            driver.switch_to.window(panel_handle)
            driver.set_window_size(1280, 900)

            # Reproduce a stale error in an already open panel after a vault
            # moves. Discovery alone must be distinct from applying its path.
            cfg['vault'] = str(run_dir / 'moved-again')
            cfg['vault_mode'] = 'manual'
            config_path.write_text(json.dumps(cfg))
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.set({settingsRevision:crypto.randomUUID()}).then(done);')
            wait.until(lambda d: 'No encuentro el vault' in d.find_element(By.ID, 'error').text)
            options_handle = open_options_from_panel()
            Select(driver.find_element(By.ID, 'vault_mode')).select_by_value('auto')
            wait.until(lambda d: not d.find_element(By.ID, 'detect-vaults').get_attribute('disabled'))
            Select(driver.find_element(By.ID, 'detected-vault')).select_by_value(str(vault))
            assert 'Aún no está en uso' in driver.find_element(By.ID, 'message').text
            assert message({'type': 'native', 'message': {'action': 'settings'}})['config']['vault'] == cfg['vault']
            driver.find_element(By.ID, 'save-and-back').click()
            wait.until(lambda d: options_handle not in d.window_handles)
            driver.switch_to.window(panel_handle)
            wait.until(lambda d: d.find_element(By.ID, 'connection').text == 'SERVICIO LOCAL CONECTADO')
            wait.until(lambda d: not d.find_element(By.ID, 'error').is_displayed())
            applied = message({'type': 'native', 'message': {'action': 'settings'}})
            assert applied['config']['vault'] == str(vault) and applied['vault_available']
            (out / 'options-report.json').write_text(json.dumps({
                'passed': True, 'automatic_selection_persisted': True,
                'manual_path_persisted': True, 'invalid_path_rejected': True,
                'missing_vault_settings_recovered': True, 'detected_paths': detected,
                'back_visible_after_scroll_at_420px': True, 'no_horizontal_overflow': True,
                'direct_options_returns_to_capture': True, 'options_tab_returns_to_opener': True,
                'unsaved_changes_survive_navigation': True, 'unsaved_changes_not_applied': True,
                'saved_changes_clear_local_draft': True,
                'discovered_vault_marked_pending_until_save': True,
                'save_and_return_applies_detected_vault': True,
                'existing_panel_clears_missing_vault_error': True,
                'all_saves_use_fixture_vault': str(vault)
            }, ensure_ascii=False, indent=2))
            driver.get(panel)
            wait.until(lambda d: 'CONECTADO' in d.find_element(By.ID, 'connection').text)
        def capture(input,target_url=None):
            file_tab=None
            if target_url and target_url.startswith('file:'):
                before=set(driver.window_handles)
                file_tab=driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.create({url:"about:blank",active:false}).then(done);')
                handle=wait.until(lambda d:next(iter(set(d.window_handles)-before),None))
                driver.switch_to.window(handle);driver.get(target_url)
                driver.switch_to.window(panel_handle)
            # Zen does not implement WebDriver newWindow; create the test source
            # through the installed extension, keeping its review panel active.
            result=driver.execute_async_script('''const done=arguments[arguments.length-1], targetURL=arguments[0], input=arguments[1], existing=arguments[2];
              browser.runtime.getBackgroundPage().then(async bg=>{
                const tab=existing?await browser.tabs.get(existing):await browser.tabs.create({url:targetURL,active:false});
                for(let i=0;i<200;i++){const now=await browser.tabs.get(tab.id);if(now.status==='complete'&&now.url===targetURL)break;await new Promise(r=>setTimeout(r,50));}
                const current=await browser.tabs.get(tab.id);
                const c=await bg.capture(current,input);done({ok:true,result:c});
              }).catch(e=>done({ok:false,error:e.message}));''',target_url or url,input,file_tab['id'] if file_tab else None)
            assert result["ok"],result
            wait.until(lambda d:not d.find_element(By.ID,"captureCard").get_attribute("hidden"))
            return result["result"]

        def source_script(tab_id,code):
            result=driver.execute_async_script('''const done=arguments[arguments.length-1],id=arguments[0],code=arguments[1];
              browser.tabs.executeScript(id,{code}).then(result=>done({ok:true,result:result[0]}),e=>done({ok:false,error:e.message}));''',tab_id,code)
            assert result["ok"],result
            return result["result"]

        def review_status():
            return driver.execute_async_script('const done=arguments[arguments.length-1],id=new URL(location.href).searchParams.get("capture");browser.storage.local.get("reviewSessions").then(s=>done(s.reviewSessions?.[id]||{}));')

        def review_control(command,note=None,value=None):
            session=wait.until(lambda d:review_status())
            return message({'type':'reviewCommand','id':session['id'],'windowId':session['windowId'],'command':command,'note':note,'value':value})

        def open_review(allow_blocked=False):
            def ready(d):
                if d.find_element(By.ID,"error").is_displayed():raise AssertionError(d.find_element(By.ID,"error").text)
                return d.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.get(["reviews","currentCapture"]).then(s=>done(s.reviews?.[s.currentCapture?.id]?s.currentCapture.id:false));')
            try:expected=WebDriverWait(driver,210 if args.ai else 30).until(ready)
            except Exception:
                # Diagnosis of the review that never opened: storage and open tabs.
                state=driver.execute_async_script('const done=arguments[arguments.length-1];Promise.all([browser.storage.local.get(["reviews","currentCapture","operation","operationError","activeWork","reviewSessions"]),browser.tabs.query({})]).then(([s,tabs])=>done({reviews:s.reviews,capture:s.currentCapture?.id,operation:s.operation,operationError:s.operationError,activeWork:s.activeWork,sessions:Object.keys(s.reviewSessions||{}),tabs:tabs.map(t=>({id:t.id,url:t.url,active:t.active}))}));')
                (out/'review-timeout.json').write_text(json.dumps({'state':state,'handles':len(driver.window_handles),'error':driver.find_element(By.ID,'error').text},indent=2,ensure_ascii=False))
                raise
            for handle in driver.window_handles:
                driver.switch_to.window(handle)
                if driver.current_url==panel.replace("panel.html","review.html")+"?capture="+expected:
                    driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.getCurrent().then(tab=>browser.tabs.update(tab.id,{active:true})).then(done);')
                    wait.until(lambda d:d.find_element(By.ID,"workspace").is_displayed() and (allow_blocked or review_status().get('canSave')))
                    return handle
            raise AssertionError("No se abrió la pestaña de revisión")

        def finish_and_return(decision,source_id):
            review_handle=driver.current_window_handle
            review_tab_id=driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.getCurrent().then(tab=>done(tab.id));')
            driver.execute_async_script('''const done=arguments[arguments.length-1];browser.runtime.getBackgroundPage().then(bg=>{
              bg.testTabEvents=[];bg.browser.tabs.onActivated.addListener(info=>bg.testTabEvents.push({event:'active',id:info.tabId}));
              bg.browser.tabs.onRemoved.addListener(id=>bg.testTabEvents.push({event:'removed',id}));done(true);});''')
            if decision=='save':
                wait.until(lambda d:review_status().get('canSave'))
                review_control('save')
            else:
                wait.until(lambda d:not d.find_element(By.ID,decision).get_attribute('disabled'))
                driver.find_element(By.ID,decision).click()
            try:wait.until(lambda d:review_handle not in d.window_handles)
            except Exception:
                (out/'review-timeout.json').write_text(json.dumps({'step':'finish','error':driver.find_element(By.ID,'error').text,'success':driver.find_element(By.ID,'success').text,
                    'filename':driver.find_element(By.ID,'filename').get_attribute('value'),'status':review_status()},indent=2,ensure_ascii=False))
                raise
            driver.switch_to.window(panel_handle)
            events=driver.execute_async_script('const done=arguments[arguments.length-1];browser.runtime.getBackgroundPage().then(bg=>done(bg.testTabEvents));')
            if source_id is not None:
                assert any(e["event"]=="active" and e["id"]==source_id for e in events),events
            else:
                before_removed=events[:next(i for i,e in enumerate(events) if e["event"]=="removed" and e["id"]==review_tab_id)]
                active=[e["id"] for e in before_removed if e["event"]=="active"]
                assert active,events
                reopened=driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.get(arguments[0]).then(tab=>done(tab.url));',active[-1])
                assert reopened==url,reopened
            return events
        def open_manual_importer():
            target=panel+'?import=1'
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.create({url:arguments[0],active:true}).then(done);',target)
            def find(d):
                for handle in d.window_handles:
                    d.switch_to.window(handle)
                    if d.current_url==target:return handle
                return False
            handle=wait.until(find)
            wait.until(lambda d:d.find_element(By.ID,'fileImport').is_displayed())
            return handle
        if args.review_menu:
            c=capture({});Select(field('provider')).select_by_value('codex');driver.find_element(By.ID,'prepare').click();open_review()
            review_handle=driver.current_window_handle;capture_id=driver.current_url.split('capture=')[1]
            wait.until(lambda d:'candidatas revisadas' in d.find_element(By.ID,'connectionStatus').text)
            assert not driver.find_elements(By.CSS_SELECTOR,'#save,#readTab,#editTab,#proposeSplit,#refreshConnections,#noteList,#mobileProperties')
            # A real click can recover the native sidebar without losing the
            # user gesture required by Firefox or starting another capture.
            assert not driver.execute_async_script('const done=arguments[arguments.length-1];browser.sidebarAction.isOpen({}).then(done);')
            wait.until(lambda d:d.find_element(By.ID,'openReviewPanel').is_enabled())
            driver.find_element(By.ID,'openReviewPanel').click()
            wait.until(lambda d:d.execute_async_script('const done=arguments[arguments.length-1];browser.sidebarAction.isOpen({}).then(done);'))
            wait.until(lambda d:d.execute_async_script('const done=arguments[arguments.length-1];browser.runtime.getBackgroundPage().then(bg=>done(bg.browser.extension.getViews({type:"sidebar"}).some(v=>v.document.getElementById("reviewWorkspace")?.hidden===false)));'))
            driver.save_screenshot(str(out/'review-with-sidebar.png'))
            sidebar_window=driver.execute_async_script('const done=arguments[arguments.length-1];browser.windows.getCurrent().then(w=>done(w.id));')
            driver.set_context('chrome')
            driver.execute_script('const owner=[...Services.wm.getEnumerator("navigator:browser")].find(w=>w.docShell.outerWindowID===arguments[0]);owner.SidebarController.hide();',sidebar_window)
            driver.set_context('content')
            driver.switch_to.window(panel_handle)
            wait.until(lambda d:d.find_element(By.ID,'reviewWorkspace').is_displayed())
            assert not driver.find_element(By.ID,'captureWorkspace').is_displayed()
            assert len(driver.find_elements(By.CSS_SELECTOR,'[data-review-note]'))==4
            driver.save_screenshot(str(out/'menu.png'))
            driver.find_element(By.CSS_SELECTOR,'[data-review-note="comprension"]').click()
            driver.switch_to.window(review_handle)
            wait.until(lambda d:'Comprender lo estudiado' in d.find_element(By.ID,'activeNoteLabel').text)
            wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,'#relations .relation'))>0)
            wait.until(lambda d:d.find_element(By.CSS_SELECTOR,'[data-new-link="recuperacion"]').is_selected())
            driver.switch_to.window(panel_handle);driver.find_element(By.ID,'reviewEdit').click();driver.switch_to.window(review_handle)
            wait.until(lambda d:d.find_element(By.ID,'editPane').is_displayed())
            driver.switch_to.window(panel_handle)
            wait.until(lambda d:d.find_element(By.ID,'reviewEdit').get_attribute('aria-pressed')=='true' and d.find_element(By.ID,'reviewRead').get_attribute('aria-pressed')=='false')
            driver.switch_to.window(review_handle)
            driver.find_element(By.ID,'body').send_keys('\n\nAPORTE DESDE EL MENÚ: debe conservarse.')
            wait.until(lambda d:review_status().get('canSave'))
            driver.switch_to.window(panel_handle)
            wait.until(lambda d:d.find_element(By.ID,'reviewSave').is_enabled())
            checkbox=driver.find_element(By.CSS_SELECTOR,'[data-review-note="revision"]').find_element(By.XPATH,'../input')
            checkbox.click();driver.switch_to.window(review_handle)
            wait.until(lambda d:'Guardar 3 notas' in review_status().get('saveLabel',''))
            driver.switch_to.window(panel_handle)
            wait.until(lambda d:'3 de 4' in d.find_element(By.ID,'reviewMenuStatus').text)
            driver.find_element(By.CSS_SELECTOR,'[data-review-note="recuperacion"]').click();driver.switch_to.window(review_handle)
            wait.until(lambda d:'Recuperar sin mirar' in d.find_element(By.ID,'activeNoteLabel').text)
            wait.until(lambda d:d.find_element(By.CSS_SELECTOR,'[data-new-link="comprension"]').is_selected())
            # Exact narrow-panel viewport with the live assistant state.
            driver.switch_to.window(panel_handle)
            driver.execute_script('const f=document.createElement("iframe");f.id="menu-narrow";f.src=location.href;f.style="position:fixed;inset:0 auto auto 0;width:240px;height:900px;border:0;z-index:1000";document.body.append(f);')
            driver.switch_to.frame(driver.find_element(By.ID,'menu-narrow'))
            wait.until(lambda d:d.find_element(By.ID,'reviewWorkspace').is_displayed())
            assert driver.execute_script('return innerWidth===240&&document.documentElement.scrollWidth<=document.documentElement.clientWidth')
            driver.save_screenshot(str(out/'menu-narrow.png'));driver.switch_to.default_content();driver.execute_script('document.getElementById("menu-narrow").remove()')
            extra=message({'type':'native','message':{'action':'capture','capture':{'kind':'quote','title':'Segunda revisión independiente','url':'https://example.org/second-review','text':'Una segunda frase para comprobar qué revisión controla el menú lateral.','images':[]}}})
            message({'type':'native','message':{'action':'draft','id':extra['id'],'provider':'manual'}})
            handles=set(driver.window_handles);extra_review=message({'type':'openReview','id':extra['id']})
            extra_handle=wait.until(lambda d:next(iter(set(d.window_handles)-handles),None));driver.switch_to.window(extra_handle)
            wait.until(lambda d:d.find_element(By.ID,'workspace').is_displayed() and review_status().get('canSave'))
            driver.switch_to.window(panel_handle)
            wait.until(lambda d:d.find_element(By.ID,'reviewChooser').is_displayed() and d.find_element(By.ID,'reviewChooser').get_attribute('value')==extra['id'])
            assert len(driver.find_elements(By.CSS_SELECTOR,'[data-review-note]'))==1
            Select(driver.find_element(By.ID,'reviewChooser')).select_by_value(capture_id)
            wait.until(lambda d:d.find_element(By.ID,'reviewChooser').get_attribute('value')==capture_id and len(d.find_elements(By.CSS_SELECTOR,'[data-review-note]'))==4)
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.remove(arguments[0]).then(done);',extra_review['tabId'])
            wait.until(lambda d:not d.find_element(By.ID,'reviewChooser').is_displayed())
            # A different article in the same window does not leave review mode.
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.update(arguments[0],{active:true}).then(done);',c['source']['tabId'])
            assert driver.find_element(By.ID,'reviewWorkspace').is_displayed()
            driver.find_element(By.ID,'reviewFocus').click()
            # Closing manually restores capture; reopening keeps all edits.
            review_tab=driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.get("reviewSessions").then(s=>done(s.reviewSessions[arguments[0]].tabId));',capture_id)
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.remove(arguments[0]).then(done);',review_tab)
            wait.until(lambda d:not d.find_element(By.ID,'reviewWorkspace').is_displayed() and d.find_element(By.ID,'captureWorkspace').is_displayed())
            message({'type':'resume','id':capture_id});open_review();review_handle=driver.current_window_handle
            wait.until(lambda d:review_status().get('canSave'))
            driver.switch_to.window(panel_handle)
            wait.until(lambda d:d.find_element(By.ID,'reviewWorkspace').is_displayed() and d.find_element(By.ID,'reviewSave').is_enabled())
            driver.find_element(By.ID,'reviewSave').click()
            wait.until(lambda d:review_handle not in d.window_handles)
            wait.until(lambda d:not d.find_element(By.ID,'reviewWorkspace').is_displayed())
            saved=[p for p in vault.rglob('*.md') if p.name not in ('recuperacion_activa.md','recuperacion_paquetes.md')]
            assert len(saved)==3
            assert sum('APORTE DESDE EL MENÚ: debe conservarse.' in p.read_text() for p in saved)==1
            report={'passed':True,'no_duplicate_review_menu':True,'open_native_sidebar_from_review_click':True,'active_read_edit_state':True,'review_replaces_capture_controls':True,'navigate_and_edit_from_menu':True,'selection_synced':True,'external_suggestions_per_theme':True,'sibling_links_both_directions':True,'exact_240px_no_horizontal_overflow':True,'multiple_reviews_follow_focus':True,'review_mode_kept_across_tabs':True,'manual_close_restores_capture':True,'reopen_preserves_edits':True,'save_from_menu':True,'saved_notes':3,'vault':str(vault)}
            (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,indent=2));return
        if args.split_review:
            fixture_notes={str(p.relative_to(vault)):p.read_bytes() for p in vault.rglob('*.md')}
            c=capture({});driver.find_element(By.ID,'prepare').click();open_review()
            capture_id=driver.current_url.split('capture=')[1]
            before=message({'type':'native','message':{'action':'load','id':capture_id}})
            assert not before.get('bundle')
            review_control('edit')
            body=driver.find_element(By.ID,'body');body.send_keys('\n\n## Comentario personal\nMI COMENTARIO PARA LA DIVISIÓN: conservarlo exactamente.')
            edited=body.get_attribute('value');review_control('read')
            wait.until(lambda d:d.find_element(By.ID,'previewState').text=='Vista actualizada')
            review_control('split')
            wait.until(lambda d:d.find_element(By.ID,'splitDialog').get_attribute('open'))
            assert len(driver.find_elements(By.CSS_SELECTOR,'#splitNotes>section'))==2
            assert message({'type':'native','message':{'action':'load','id':capture_id}})==before
            assert {str(p.relative_to(vault)):p.read_bytes() for p in vault.rglob('*.md')}==fixture_notes
            driver.save_screenshot(str(out/'suggestion.png'))
            driver.find_element(By.ID,'rejectSplit').click()
            wait.until(lambda d:not d.find_element(By.ID,'splitDialog').get_attribute('open'))
            assert driver.find_element(By.ID,'body').get_attribute('value')==edited
            assert message({'type':'native','message':{'action':'load','id':capture_id}})==before
            review_control('split')
            wait.until(lambda d:d.find_element(By.ID,'splitDialog').get_attribute('open'))
            driver.find_element(By.ID,'acceptSplit').click()
            wait.until(lambda d:'Guardar 3 notas' in review_status().get('saveLabel',''))
            wait.until(lambda d:review_status().get('canSave'))
            stored=message({'type':'native','message':{'action':'load','id':capture_id}})
            assert len(stored['bundle']['notes'])==2
            assert {str(p.relative_to(vault)):p.read_bytes() for p in vault.rglob('*.md')}==fixture_notes
            content='\n'.join(n['body'] for n in stored['bundle']['notes'])
            assert content.count('MI COMENTARIO PARA LA DIVISIÓN: conservarlo exactamente.')==1
            assert 'estudiar()\nrecordar()\nrevisar()' in content
            driver.refresh()
            wait.until(lambda d:d.find_element(By.ID,'workspace').is_displayed() and review_status().get('canSave'))
            assert len(review_status()['notes'])==3
            driver.save_screenshot(str(out/'accepted.png'));finish_and_return('save',c['source']['tabId'])
            report={'passed':True,'suggestion_does_not_change_draft':True,'discard_preserves_note_and_edits':True,'accept_requires_user_click':True,'code_and_personal_annotation_preserved':True,'accepted_split_survives_reload':True,'review_before_save':True,'saved_new_notes':3,'vault':str(vault)}
            (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,indent=2));return
        if args.profile:
            wait.until(lambda d:not d.find_element(By.ID,'profileNotice').get_attribute('hidden'))
            assert 'aún no tiene perfil' in driver.find_element(By.ID,'profileNoticeText').text
            driver.save_screenshot(str(out/'panel-missing.png'))
            panel_url=driver.current_url;driver.get(panel.replace('panel.html','options.html'))
            wait.until(lambda d:'aún no tiene perfil' in d.find_element(By.ID,'profileStatus').text)
            driver.find_element(By.ID,'profileScan').click()
            wait.until(lambda d:d.find_element(By.ID,'profileDocs').is_displayed())
            docs={b.get_attribute('value'):b.is_selected() for b in driver.find_elements(By.CSS_SELECTOR,'#profileDocList input')}
            assert docs.get('AGENTS.md') and docs.get('99_Recursos/guias/guia_frontmatter_y_relaciones.md') and '00_Sistema/identidad_viva.md' not in docs,docs
            driver.find_element(By.ID,'profileAutomatic').click()
            wait.until(lambda d:d.find_element(By.ID,'profileReview').is_displayed())
            form=driver.find_element(By.ID,'profileForm').text
            # The review opens on a short summary; every section starts folded.
            summary=driver.find_element(By.CSS_SELECTOR,'#profileForm .profile-summary').text
            assert 'Guarda en' in summary and '02_Cerebro' in summary,summary
            assert not any(d.get_attribute('open') for d in driver.find_elements(By.CSS_SELECTOR,'#profileForm details.profile-section'))
            assert len(form.splitlines())<40,len(form.splitlines())
            proposed=json.loads(driver.find_element(By.ID,'profileJson').get_attribute('value'))
            assert len(proposed['destinations'])<=4 and 'relacionadas' in [f['key'] for f in proposed['frontmatter']],proposed
            assert not any(r['pattern'].startswith(('05_Archivo_Legacy','00_Sistema','01_Diario','99_Recursos')) for r in proposed['destinations']),proposed['destinations']
            assert driver.find_element(By.ID,'profilePath').get_attribute('value')=='99_Recursos/anaco/perfil.json'
            driver.save_screenshot(str(out/'options-review.png'))
            driver.execute_script('arguments[0].scrollIntoView()',driver.find_element(By.ID,'profileSave'));driver.find_element(By.ID,'profileSave').click()
            wait.until(lambda d:'Perfil guardado' in d.find_element(By.ID,'message').text)
            assert (vault/'99_Recursos/anaco/perfil.json').is_file()
            wait.until(lambda d:'Perfil confirmado' in d.find_element(By.ID,'profileStatus').text)
            driver.get(panel_url);wait.until(lambda d:d.find_element(By.ID,'profileNotice').get_attribute('hidden'))
            before={p for p in vault.rglob('*.md')}
            c=capture({});Select(field('provider')).select_by_value('manual')
            driver.find_element(By.ID,'prepare').click();open_review()
            finish_and_return('save',c['source']['tabId'])
            created=[p for p in vault.rglob('*.md') if p not in before]
            assert len(created)==1,created
            note=created[0].read_text();(out/'note.md').write_text(note)
            assert created[0].parent.name=='Tech_&_Codigo' and created[0].name.startswith('nota_'),created[0]
            for line in ('tipo: "nota_atomica"','zona: "cerebro"','area: "tech_codigo"','relacionadas: []'):assert line in note,(line,note[:600])
            for old in ('version:','estado:','llm_asistido:'):assert old not in note.split('---')[1],(old,note[:600])
            (vault/'99_Recursos/guias/MANUAL_VAULT.md').rename(vault/'MANUAL_VAULT.md')
            problems=message({'type':'native','message':{'action':'status'}})['profile']['problems']
            assert any('MANUAL_VAULT.md' in p for p in problems),problems
            driver.get(panel_url);wait.until(lambda d:'MANUAL_VAULT.md' in d.find_element(By.ID,'profileNoticeText').text)
            driver.save_screenshot(str(out/'panel-review.png'))
            report={'passed':True,'missing_profile_notice':True,'scan_documents_without_private_notes':True,'automatic_proposal_reviewed':True,'profile_saved':'99_Recursos/anaco/perfil.json',
                    'note':created[0].relative_to(vault).as_posix(),'vault_frontmatter':True,'old_fields_absent':True,'moved_guide_asks_review':True}
            (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps(report,indent=2,ensure_ascii=False));return
        if args.embeds_live:
            live='https://tympanus.net/codrops/2026/10/16/ksenia-kondrashova/'
            c=capture({},live)
            for _ in range(20):
                if len(c.get('embeds',[]))>=12:break
                time.sleep(1.5);c=capture({},live)
            counts={t:sum(e['type']==t for e in c['embeds']) for t in ('clip','pen','tweet')}
            assert counts['clip']>=5 and counts['pen']>=1 and counts['tweet']>=1,counts
            assert 'Ksenia' in c['text'] and not c.get('requiredOrigins'),(c['text'][:300],c.get('requiredOrigins'))
            assert not any(v['url'].endswith('-optimized.mp4') for v in c['videos']),c['videos']
            wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,'#embeds input[type=checkbox]'))==len(c['embeds']))
            driver.save_screenshot(str(out/'panel.png'))
            # Keep the run light: two clips, every pen and post.
            clips=[e['index'] for e in c['embeds'] if e['type']=='clip']
            for box in driver.find_elements(By.CSS_SELECTOR,'#embeds input[type=checkbox]'):
                if int(box.get_attribute('data-embed')) in clips[2:] and box.is_selected():driver.execute_script('arguments[0].click()',box)
            Select(field('provider')).select_by_value('manual')
            driver.find_element(By.ID,'prepare').click();open_review(allow_blocked=True)
            current=message({'type':'native','message':{'action':'load','id':driver.current_url.split('capture=')[1]}})
            driver.save_screenshot(str(out/'review.png'))
            finish_and_return('save',c['source']['tabId'])
            note=next(vault.rglob('fuente_*.md')).read_text();(out/'note.md').write_text(note)
            pages=list(vault.rglob('index.html'))
            report={'passed':True,'counts':counts,'text_chars':len(c['text']),'clips_saved':len(list(vault.rglob('*.mp4'))),'offline_demos':len(pages),
                    'libraries':sorted(p.name for page in pages for p in page.parent.iterdir() if p.suffix in ('.js','.css')),'warnings':current['warnings']}
            (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps(report,indent=2,ensure_ascii=False));return
        if args.embeds:
            base=url.rsplit('/',1)[0]
            def mode(value):
                Select(driver.find_element(By.ID,'captureMode')).select_by_value(value)
                wait.until(lambda d:d.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.get("captureMode").then(s=>done(s.captureMode));')==value)
            # Course mode is the previous detection: no embeds, the clip is a video to transcribe.
            mode('course');classic=capture({},base+'/embeds-article.html')
            assert not classic.get('embeds') and '{{recurso' not in classic['text'],classic.get('embeds')
            assert any('lesson.mp4' in v['url'] for v in classic['videos']),classic['videos']
            nested=capture({},base+'/widget-article.html');assert 'WIDGET TEXT' in nested['text'] and 'THE ARTICLE TEXT' not in nested['text']
            mode('auto');auto_widget=capture({},base+'/widget-article.html');assert auto_widget['text']==nested['text']
            mode('article');article=capture({},base+'/widget-article.html');assert 'THE ARTICLE TEXT' in article['text'] and 'WIDGET TEXT' not in article['text']
            mode('auto');c=capture({},base+'/embeds-article.html')
            types=[e['type'] for e in c['embeds']];assert sorted(types)==['clip','pen','tweet'],types
            for e in c['embeds']:assert '{{recurso:%d}}'%e['index'] in c['text'],(e,c['text'])
            text=c['text'];assert text.index('This introduction')<text.index('{{recurso:')<text.index('The conclusion')
            assert not any('lesson.mp4' in v['url'] for v in c['videos']),c['videos']
            assert not any('no se han transcrito' in w for w in c['warnings']),c['warnings']
            tweet=next(e for e in c['embeds'] if e['type']=='tweet');assert tweet['url']=='https://twitter.com/uuuuuulala/status/1803039502136426656' and 'Packaging people' in tweet['text'],tweet
            wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,'#embeds input[type=checkbox]'))==3)
            assert all(e.is_selected() for e in driver.find_elements(By.CSS_SELECTOR,'#embeds input[type=checkbox]'))
            driver.save_screenshot(str(out/'panel.png'))
            Select(field('provider')).select_by_value('manual')
            driver.find_element(By.ID,'prepare').click();open_review()
            current=message({'type':'native','message':{'action':'load','id':driver.current_url.split('capture=')[1]}})
            stored={e['type']:e for e in current['embeds']}
            assert stored['clip']['selected'] and stored['clip'].get('asset'),stored['clip']
            assert stored['pen']['selected'],stored['pen']
            driver.save_screenshot(str(out/'review.png'))
            finish_and_return('save',c['source']['tabId'])
            note=next(vault.rglob('fuente_*.md')).read_text()
            assert '{{recurso' not in note and '![](https://twitter.com/uuuuuulala/status/1803039502136426656)' in note
            clip=next(vault.rglob('*.mp4'));assert clip.read_bytes()==(ROOT/'tests/fixtures/lesson.mp4').read_bytes()
            assert '![['+clip.relative_to(vault).as_posix()+']]' in note
            assert 'https://codepen.io/ksenia-k/pen/rNXPZRN' in note
            offline='html-preview' in note
            if offline:
                page=next(vault.rglob('index.html')).read_text();assert 'window.CP=' in page and 'unpkg.com/gsap' not in page
            (out/'note.md').write_text(note)
            report={'passed':True,'course_mode_unchanged':True,'nested_text_rule_kept_in_auto':True,'article_mode_prefers_page':True,'embeds_in_place':True,'clip_saved':True,'tweet_embed':True,'pen_offline_copy':offline,'warnings':current['warnings']}
            (out/'report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps(report,indent=2,ensure_ascii=False));return
        if args.code:
            edge=capture({},url.rsplit('/',1)[0]+'/edge-code.html')
            assert '````js\nconst text = "```";\n\n\nconst y = 2;\n````' in edge['text']
            assert '` a < b && c `' in edge['text']
            captured=capture({},url.rsplit('/',1)[0]+'/code-article.html')
            original=json.loads((ROOT/'.test-artifacts/codrops-code/source.json').read_text())
            assert len(original['code'])==17
            for block in original['code']:assert block in captured['text'],block[:100]
            assert '```' in captured['text']
            assert Select(driver.find_element(By.ID,'noteStructure')).first_selected_option.get_attribute('value')=='single'
            # A selected per-capture mode must reach the service, independently
            # of its default. Manual mode preserves text without an AI request.
            Select(driver.find_element(By.ID,'noteStructure')).select_by_value('linked')
            (out/'captured.json').write_text(json.dumps(captured,ensure_ascii=False,indent=2))
            driver.find_element(By.ID,'prepare').click();open_review()
            current=message({'type':'native','message':{'action':'load','id':captured.get('id') or driver.current_url.split('capture=')[1]}})
            assert current['note_structure']=='linked'
            for block in original['code']:assert block in current['draft']['body']
            report={'passed':True,'source':'https://tympanus.net/codrops/2026/10/13/scroll-driven-ghost-trails/','real_source_blocks':17,'all_blocks_literal':True,'nested_backticks_blank_lines_and_language_preserved':True,'inline_code_literal':True,'single_default':True,'capture_choice_reaches_service':True}
            (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return
        if args.workflow:
            c=capture({});Select(field('provider')).select_by_value('codex');driver.find_element(By.ID,'prepare').click();open_review()
            review_control('note','comprension')
            wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,'#newRelations input'))>0)
            driver.find_element(By.CSS_SELECTOR,'[data-new-link="source"]').click()
            wait.until(lambda d:'Síntesis y mapa de esta fuente' not in d.find_element(By.ID,'markdown').get_attribute('textContent'))
            driver.find_element(By.CSS_SELECTOR,'[data-new-link="source"]').click()
            wait.until(lambda d:'Síntesis y mapa de esta fuente' in d.find_element(By.ID,'markdown').get_attribute('textContent'))
            review_control('edit');body=driver.find_element(By.ID,'body');body.send_keys('\n\n## Comentario personal\nEste comentario debe conservarse exactamente.');before=body.get_attribute('value')
            driver.execute_script('arguments[0].blur();',body)
            Select(driver.find_element(By.ID,'revisionScope')).select_by_value('0')
            driver.find_element(By.CSS_SELECTOR,'[data-revise="clarify"]').click();wait.until(lambda d:d.find_element(By.ID,'revisionDialog').get_attribute('open'))
            assert 'Explicación ajustada' in driver.find_element(By.ID,'revisionAfter').text
            driver.save_screenshot(str(out/'revision.png'));driver.find_element(By.ID,'acceptRevision').click()
            wait.until(lambda d:'Explicación ajustada' in d.find_element(By.ID,'body').get_attribute('value'))
            assert driver.find_element(By.ID,'body').get_attribute('value').endswith('## Comentario personal\nEste comentario debe conservarse exactamente.')
            driver.find_element(By.ID,'undoRevision').click();assert driver.find_element(By.ID,'body').get_attribute('value')==before
            driver.find_element(By.CSS_SELECTOR,'[data-revise="clarify"]').click();wait.until(lambda d:d.find_element(By.ID,'revisionDialog').get_attribute('open'));driver.find_element(By.ID,'acceptRevision').click()
            Select(driver.find_element(By.ID,'mergeNote')).select_by_value('revision');driver.find_element(By.ID,'mergeButton').click();wait.until(lambda d:d.find_element(By.ID,'revisionDialog').get_attribute('open'));driver.find_element(By.ID,'acceptRevision').click()
            wait.until(lambda d:'Guardar 3 notas' in review_status().get('saveLabel',''))
            review_control('read')
            wait.until(lambda d:d.find_element(By.ID,'previewState').text=='Vista actualizada')
            stress='# Título '+('Largo'*90)+'\n\nhttps://example.org/'+('ruta'*250)+'\n\n| '+(' | '.join('Columna '+str(i) for i in range(12)))+' |\n| '+(' | '.join('---' for i in range(12)))+' |\n| '+(' | '.join('Dato '+str(i) for i in range(12)))+' |\n\n```text\n'+('codigo_sin_espacios'*100)+'\n```'
            driver.execute_script('AnacoObRender(document.getElementById("reading"),arguments[0],new Map(),()=>{},"Vault");',stress)
            for width in (480,640,950):
                driver.set_window_size(width,1000)
                dimensions=driver.execute_script('return {width:innerWidth,body:document.documentElement.scrollWidth};')
                assert dimensions['body']<=dimensions['width'],dimensions
                if width==480:driver.save_screenshot(str(out/'narrow-stress.png'))
                driver.execute_script('window.scrollTo(0,0)')
                toolbar_top=driver.execute_script('const n=document.querySelector(".note-status");return n.getBoundingClientRect().top+scrollY;')
                driver.execute_script('window.scrollTo(0,650)')
                wait.until(lambda d:d.execute_script('return scrollY>300'))
                toolbar=driver.execute_script('const n=document.querySelector(".note-status"),r=n.getBoundingClientRect();return {position:getComputedStyle(n).position,documentTop:r.top+scrollY,bottom:r.bottom};')
                assert toolbar['position']=='static' and abs(toolbar['documentTop']-toolbar_top)<1,toolbar
                assert toolbar['bottom']<0,toolbar
                if width==950:driver.save_screenshot(str(out/'toolbar-scrolled.png'))
                driver.execute_script('window.scrollTo(0,0)')
            driver.save_screenshot(str(out/'narrow.png'));driver.set_window_size(1100,1100)
            review_control('read');wait.until(lambda d:d.find_element(By.ID,'previewState').text=='Vista actualizada')
            target='02_Cerebro/Modelos_Mentales/recuperacion_activa.md';original=(vault/target).read_text()
            Select(field('saveMode')).select_by_value('append');Select(field('updateTarget')).select_by_value(target)
            wait.until(lambda d:'Se añadirá al final' in d.find_element(By.ID,'updateDiff').text)
            assert not review_status().get('canSave')
            driver.find_element(By.ID,'approveUpdate').click();wait.until(lambda d:review_status().get('canSave'))
            review_control('note','source');field('title').send_keys(' revisado')
            wait.until(lambda d:not review_status().get('canSave'))
            review_control('note','comprension')
            wait.until(lambda d:not d.find_element(By.ID,'approveUpdate').is_selected())
            review_control('read');wait.until(lambda d:d.find_element(By.ID,'previewState').text!='Actualizando…')
            assert not review_status().get('canSave')
            driver.find_element(By.ID,'approveUpdate').click();wait.until(lambda d:review_status().get('canSave'))
            driver.save_screenshot(str(out/'amendment.png'));finish_and_return('save',c['source']['tabId'])
            assert (vault/target).read_text().startswith(original);assert 'Explicación ajustada' in (vault/target).read_text();assert 'Este comentario debe conservarse exactamente.' in (vault/target).read_text()
            # The first CLI attempt really sleeps; cancellation must stop it, then resume its stored request.
            (run_dir/'delay-once').write_text('delay');q=capture({'kind':'quote','selection':'Una nueva captura para comprobar la cancelación y la reanudación de un trabajo en segundo plano.'})
            Select(field('provider')).select_by_value('codex');driver.find_element(By.ID,'prepare').click();wait.until(lambda d:(run_dir/'delay-started').exists() and d.find_element(By.ID,'workCard').is_displayed())
            driver.find_element(By.ID,'cancelJob').click();wait.until(lambda d:not d.find_element(By.ID,'workCard').is_displayed());wait.until(lambda d:d.find_element(By.ID,'recoverSection').is_displayed())
            driver.find_element(By.CSS_SELECTOR,'#recoverJobs button').click();open_review(True);finish_and_return('discard',q['source']['tabId'])
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.set({autoReview:true}).then(done);')
            v=capture({},url.replace('article.html','session-course.html?mode=captions'));Select(field('provider')).select_by_value('codex');driver.find_element(By.ID,'extractVideo').click();open_review(True)
            assert 'IAM controla' in message({'type':'native','message':{'action':'load','id':driver.execute_script('return new URL(location.href).searchParams.get("capture")')}})['text']
            finish_and_return('discard',v['source']['tabId'])
            report={'passed':True,'browser':driver.capabilities['browserVersion'],'scoped_revision_preserves_comments':True,'accept_and_undo':True,'merge_adjusts_note_count':True,'responsive_widths_checked':[480,640,950],'view_toolbar_does_not_follow_scroll':True,'append_preserves_existing_content':True,'explicit_amendment_approval':True,'cancel_stops_real_cli_process':True,'resume_opens_review':True,'extract_opens_review_automatically':True,'vault':str(vault)}
            (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2));return
        if args.session_video:
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.runtime.getBackgroundPage().then(bg=>{bg.testProgress=[];bg.browser.storage.onChanged.addListener(c=>{if(c.operationProgress?.newValue)bg.testProgress.push(c.operationProgress.newValue);});done(true);});')
            results={}
            for mode in ('direct','captions','hls','blocked'):
                c=capture({},url.replace('article.html','session-course.html?mode='+mode))
                video=c['videos'][0];assert video['frameId']!=0 and 'session-player.html' in video['frameURL'],video
                if mode=='direct':
                    status=driver.execute_async_script('const done=arguments[arguments.length-1];fetch(arguments[0],{credentials:"include"}).then(r=>done(r.status));',video['url'])
                    assert status==403,status
                driver.find_element(By.ID,'extractVideo').click()
                def complete(d):
                    s=d.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.get(["currentCapture","operation","operationError","operationDiagnostic","activeWork"]).then(done);')
                    if s.get('operation'):return False
                    if s.get('operationError'):
                        if mode=='blocked':return s
                        raise AssertionError(s)
                    return s if s.get('currentCapture',{}).get('id') else False
                state=WebDriverWait(driver,180).until(complete)
                if mode=='blocked':
                    assert '403' in state['operationError'];assert not state.get('activeWork')
                    attempts=state['operationDiagnostic']['attempts']
                    assert {v['context'] for v in attempts if v.get('status')==403}=={'player','extension'},attempts
                    wait.until(lambda d:'extraction' in d.find_element(By.ID,'detectionReport').get_attribute('textContent'))
                    diagnostic=driver.find_element(By.ID,'detectionReport').get_attribute('textContent');assert 'DO_NOT_COPY' not in diagnostic
                    driver.save_screenshot(str(out/'blocked-diagnostic.png'));results[mode]={'explicit_error':True,'both_contexts_reported':True,'signed_urls_omitted':True};continue
                imported=state['currentCapture'];assert imported['kind']=='video' and len(imported['text'])>20,imported
                assert imported['source']['tabId']==c['source']['tabId']
                if mode=='captions':assert 'IAM controla el acceso' in imported['text']
                else:assert 'Whisper' in imported['media']['method'] and '[00:' in imported['text']
                results[mode]={'captured':True,'method':imported['media']['method'],'characters':len(imported['text'])}
                Select(field('provider')).select_by_value('manual');driver.find_element(By.ID,'prepare').click();open_review()
                finish_and_return('save' if mode=='direct' else 'discard',c['source']['tabId'])
            assert any(v['status']==200 and v['player_referrer'] and v['session'] for v in session_requests)
            progress=driver.execute_async_script('const done=arguments[arguments.length-1];browser.runtime.getBackgroundPage().then(bg=>done(bg.testProgress));')
            assert any(v.get('stage')=='model' for v in progress),progress
            assert any(v.get('stage')=='transcribe' and v.get('processed_seconds',0)>0 and v.get('total_seconds',0)>0 for v in progress),progress
            assert any(v.get('stage')=='frames' for v in progress),progress
            results['progress']={'real_worker_updates':True,'phases':[v.get('stage') for v in progress]}
            report={'passed':True,'browser':driver.capabilities['browserVersion'],'background_fetch_reproduces_403':True,'same_player_context_downloads':True,'cases':results,'requests':session_requests,'vault':str(vault)}
            (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2));return
        if args.quality:
            driver.set_window_size(480,960)
            c=capture({},url.replace('article.html','gallery.html'));assert len(c['images'])==24,len(c['images'])
            checks=driver.find_elements(By.CSS_SELECTOR,'#images input[type=checkbox]');assert len(checks)==24
            for check in checks[:8]:driver.execute_script('arguments[0].scrollIntoView({block:"center"});',check);check.click()
            assert '8 / 8' in driver.find_element(By.ID,'imageCount').text
            assert all(not check.is_enabled() for check in checks[8:])
            gallery=driver.find_element(By.ID,'images')
            assert driver.execute_script('return arguments[0].scrollHeight>arguments[0].clientHeight;',gallery)
            driver.execute_script('arguments[0].scrollTop=arguments[0].scrollHeight;window.scrollTo(0,0);',gallery)
            driver.save_screenshot(str(out/'gallery.png'))
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.set({activeWork:{id:"quality-fixture",title:arguments[0],startedAt:Date.now()-65000},operation:"Transcribiendo en el equipo…",operationProgress:{stage:"transcribe",processed_seconds:300,total_seconds:1200,engine:"Whisper base · CPU"}}).then(done);',c['title'])
            wait.until(lambda d:d.find_element(By.ID,'workCard').is_displayed())
            assert driver.find_element(By.ID,'workProgress').get_attribute('value')=='25'
            assert '5:00 de 20:00' in driver.find_element(By.ID,'workDetail').text
            assert 'CPU' in driver.find_element(By.ID,'workDetail').text
            assert not driver.find_element(By.ID,'prepare').is_enabled()
            driver.save_screenshot(str(out/'progress.png'))
            elapsed=driver.find_element(By.ID,'workElapsed').text
            wait.until(lambda d:d.find_element(By.ID,'workElapsed').text!=elapsed)
            # Working state must fit the same viewport as the resting panel,
            # even when a phase includes a long resource or engine name.
            busy_layout=[]
            phases=[('generic','Preparando la propuesta…',''),('model','Cargando el modelo de transcripción local…',''),('download','Sin subtítulos accesibles. Descargando audio para transcribir…',''),('subtitles','Recuperando los subtítulos de la plataforma…',''),('transcribe','Transcribiendo en el equipo…','Whisper base · CPU'),('inspect','Comprobando duración y pista de audio…',''),('frames','Transcripción terminada. Extrayendo fotogramas…',''),('resource','Leyendo '+('recurso_sin_espacios_'*30)+'.pdf','motor_'+('nombre_largo_'*30))]
            # Zen can impose a minimum native window width. A same-extension
            # frame gives the real panel an exact, measurable CSS viewport.
            driver.execute_script('const f=document.createElement("iframe");f.id="busy-layout-frame";f.src=location.href;f.style="position:fixed;inset:0 auto auto 0;width:300px;height:920px;border:0;z-index:1000";document.body.append(f);')
            for width in (360,300,240,200):
                driver.switch_to.default_content()
                frame=driver.find_element(By.ID,'busy-layout-frame')
                driver.execute_script('arguments[0].style.width=arguments[1]+"px";',frame,width)
                driver.switch_to.frame(frame)
                wait.until(lambda d:d.execute_script('return innerWidth')==width)
                for stage,operation,engine in phases:
                    driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.set({activeWork:{id:"quality-fixture",title:"Nombre_sin_espacios_".repeat(30),startedAt:Date.now()-360065000},operation:arguments[1],operationProgress:{stage:arguments[0],engine:arguments[2]}}).then(done);',stage,operation,engine)
                    wait.until(lambda d:d.find_element(By.ID,'operation').text==operation)
                    dimensions=driver.execute_script('const root=document.documentElement;return {width:innerWidth,client:root.clientWidth,scroll:root.scrollWidth,stage:document.getElementById("workStage").textContent,offenders:[...document.querySelectorAll("body *")].filter(n=>{const r=n.getBoundingClientRect();return r.width&&r.right>root.clientWidth+1;}).map(n=>({tag:n.tagName,id:n.id,class:n.className,right:n.getBoundingClientRect().right})).slice(0,12)};')
                    dimensions['textOverflow']=driver.execute_script('return ["operation","workDetail","workHint","workStage"].flatMap(id=>{const n=document.getElementById(id),box=n.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(n);return [...range.getClientRects()].filter(r=>r.width&&(r.right>box.right+1||r.left<box.left-1)).map(r=>({id,left:r.left,right:r.right,boxRight:box.right}));});')
                    busy_layout.append(dimensions)
                    (out/'busy-layout.json').write_text(json.dumps(busy_layout,ensure_ascii=False,indent=2))
                    assert dimensions['scroll']<=dimensions['client'],dimensions
                    assert not dimensions['textOverflow'],dimensions
                driver.save_screenshot(str(out/f'busy-{width}.png'))
            driver.switch_to.default_content()
            driver.execute_script('document.getElementById("busy-layout-frame").remove()')
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.set({activeWork:null,operation:"",operationProgress:null}).then(done);')
            wait.until(lambda d:not d.find_element(By.ID,'workCard').is_displayed())
            checks=driver.find_elements(By.CSS_SELECTOR,'#images input[type=checkbox]')
            driver.execute_script('arguments[0].scrollIntoView({block:"center"});',checks[0]);checks[0].click()
            assert checks[-1].is_enabled()
            driver.execute_script('arguments[0].scrollIntoView({block:"center"});',checks[-1]);checks[-1].click()
            assert '8 / 8' in driver.find_element(By.ID,'imageCount').text
            selected=[int(e.get_attribute('value')) for e in checks if e.is_selected()]
            video={**c,'selected_images':selected,'videos':[{'url':'https://youtube.googleapis.com/v/abcdefghijk','title':'youtube.googleapis.com','tracks':[]}]}
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.set({currentCapture:arguments[0]}).then(done);',video)
            wait.until(lambda d:'YouTube' in d.find_element(By.ID,'videoResource').text)
            assert 'googleapis' not in driver.find_element(By.ID,'videoResource').text
            report={'passed':True,'browser':driver.capabilities['browserVersion'],'detected_images':24,'all_images_listed':True,'independent_gallery_scroll':True,'selection_limit':8,'later_images_selectable':True,'prominent_progress':True,'measured_audio_progress':True,'elapsed_time_updates':True,'controls_disabled_while_busy':True,'friendly_youtube_name':True,'busy_layout_states':len(busy_layout),'busy_panel_no_horizontal_overflow':True}
            (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2));return
        if args.manual_import:
            fixture=run_dir/'local.vtt'
            fixture.write_text('WEBVTT\n\n00:00.000 --> 00:03.000\nLa recuperación activa ayuda a recordar.\n')
            panel_handle=open_manual_importer()
            driver.find_element(By.CSS_SELECTOR,'#fileImport summary').click()
            driver.find_element(By.ID,'importFile').send_keys(str(fixture))
            driver.find_element(By.ID,'importButton').click()
            wait.until(lambda d:d.find_element(By.ID,'prepare').is_displayed())
            driver.save_screenshot(str(out/'import.png'))
            current=driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.get("currentCapture").then(s=>done(s.currentCapture));')
            assert 'La recuperación activa' in current['text']
            assert current['source']['url']==panel+'?import=1',current['source']
            Select(field('provider')).select_by_value('manual')
            driver.find_element(By.ID,'prepare').click();open_review()
            finish_and_return('discard',current['source']['tabId'])
            report={'passed':True,'importer_separate':True,'source_preserved':True,'local_subtitles':True,'review_and_discard':True}
            (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
            return
        if args.editorial:
            c=capture({})
            Select(field('provider')).select_by_value('codex')
            driver.find_element(By.ID,'prepare').click();open_review()
            assert len(review_status()['notes'])==4
            driver.find_element(By.CSS_SELECTOR,'#reading a.wiki-link').click()
            wait.until(lambda d:d.find_element(By.ID,'title').get_attribute('value')=='Comprender lo estudiado')
            field('filename').clear();field('filename').send_keys('nota_comprension_revisada.md')
            review_control('edit');driver.find_element(By.ID,'body').send_keys('\n\nAportación personal que debe conservarse.')
            review_control('note','recuperacion')
            review_control('note','comprension')
            assert 'Aportación personal' in driver.find_element(By.ID,'body').get_attribute('value')
            review_control('include','revision',False)
            driver.refresh()
            wait.until(lambda d:'Aportación personal' in d.find_element(By.ID,'body').get_attribute('value'))
            assert not next(n['selected'] for n in review_status()['notes'] if n['id']=='revision')
            review_control('note','source')
            wait.until(lambda d:'nota_comprension_revisada' in d.find_element(By.ID,'markdown').get_attribute('textContent'))
            markdown=driver.find_element(By.ID,'markdown').get_attribute('textContent')
            assert 'nota_revisar_los_errores' not in markdown
            wait.until(lambda d:'Guardar 3 notas' in review_status().get('saveLabel',''))
            driver.save_screenshot(str(out/'collection-review.png'))
            finish_and_return('save',c['source']['tabId'])
            notes=[p for p in vault.rglob('*.md') if p.name not in ('recuperacion_activa.md','recuperacion_paquetes.md')]
            assert len(notes)==3,notes
            edited=next(p for p in notes if p.name=='nota_comprension_revisada.md')
            assert 'Aportación personal' in edited.read_text()
            assert 'Síntesis y mapa de esta fuente' in edited.read_text()
            assert all('nota_revisar_los_errores' not in p.read_text() for p in notes)
            assert any('nota_comprension_revisada|' in p.read_text() for p in notes if p!=edited)
            report={'passed':True,'browser':driver.capabilities['browserVersion'],'proposed_notes':4,'saved_notes':3,
                    'editable_individual_notes':True,'wiki_navigation':True,'rename_updates_links':True,'exclude_prunes_links':True,
                    'reload_preserves_edits_and_selection':True,'reciprocal_links':True,'save_returns_to_source':True,'vault':str(vault)}
            (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
            return
        if args.book:
            c=capture({},url.replace('article.html','book-55.html'))
            assert len(c['reader']['pages'])==55,c['reader']
            assert not c['images'] and not driver.find_element(By.ID,'noteControls').is_displayed()
            assert '55' in driver.find_element(By.ID,'readerCount').text
            token=c['token']
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.runtime.getBackgroundPage().then(bg=>{bg.testCaptures=[];bg.testOperations=[];bg.browser.storage.onChanged.addListener(changes=>{if(changes.currentCapture)bg.testCaptures.push(changes.currentCapture.newValue?.token||null);if(changes.operation)bg.testOperations.push(changes.operation.newValue);});done(true);});')
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.update(arguments[0],{active:true}).then(done);',c['source']['tabId'])
            source_script(c['source']['tabId'],'window.scrollTo(0,1200);let n=0;const timer=setInterval(()=>{document.querySelector(".page").style.outlineWidth=(++n%3)+"px";if(n===20)clearInterval(timer);},35);true')
            driver.set_script_timeout(30)
            driver.execute_async_script('const done=arguments[arguments.length-1];setTimeout(done,2200);')
            driver.switch_to.window(panel_handle)
            events=driver.execute_async_script('const done=arguments[arguments.length-1];browser.runtime.getBackgroundPage().then(bg=>done(bg.testCaptures));')
            assert not events,events
            driver.save_screenshot(str(out/'book-detected.png'))
            driver.find_element(By.ID,'extractReader').click()
            # Switch to a different article while the first pages are transferring.
            switched=driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.create({url:arguments[0],active:true}).then(done);',url)
            pinned=driver.execute_async_script('const done=arguments[arguments.length-1];setTimeout(()=>browser.storage.local.get(["activeWork","currentCapture","pageContext"]).then(done),700);')
            assert pinned['activeWork']['source']['tabId']==c['source']['tabId'],pinned
            assert pinned['currentCapture']['token']==token and pinned['currentCapture']['title']==c['title'],pinned
            assert pinned['pageContext']['tabId']==c['source']['tabId'],pinned
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.update(arguments[0],{active:true}).then(done);',c['source']['tabId'])
            def received(d):
                s=d.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.get(["currentCapture","operation","operationError"]).then(done);')
                if s.get('operationError'):raise AssertionError(s['operationError'])
                return s['currentCapture'] if s.get('currentCapture',{}).get('id') and not s.get('operation') else False
            imported=WebDriverWait(driver,150).until(received)
            assert imported['reader']['captured_pages']==55 and imported['reader']['total_pages']==55
            assert 'UNIQUE PAGE 55' in imported['text']
            assert len(imported['images'])<=6
            wait.until(lambda d:source_script(c['source']['tabId'],'Math.abs(window.scrollY-1200)<3'))
            driver.switch_to.window(panel_handle)
            driver.save_screenshot(str(out/'book-extracted.png'))
            Select(field('provider')).select_by_value('codex' if args.book_ai else 'manual')
            driver.find_element(By.ID,'prepare').click();open_review()
            assert 'UNIQUE PAGE 55' in driver.find_element(By.ID,'markdown').get_attribute('textContent')
            finish_and_return('save',c['source']['tabId'])
            note=next(vault.rglob('fuente_*.md')).read_text()
            assert 'UNIQUE PAGE 55' in note and '55/55' in note
            if args.book_ai:
                calls=[json.loads(line) for line in (run_dir/'calls.jsonl').read_text().splitlines()]
                assert len([v for v in calls if v['scope']=='batch'])==10,calls
                assert [p for v in calls if v['scope']=='batch' for p in v['pages']]==list(range(1,56))
                assert calls[-1]['scope']=='synthesis'
                assert sum(v['image_count'] for v in calls)==55
                operations=driver.execute_async_script('const done=arguments[arguments.length-1];browser.runtime.getBackgroundPage().then(bg=>done(bg.testOperations));')
                assert any('55–55 de 55' in str(v) for v in operations),operations

            report={'passed':True,'pages_detected':55,'pages_extracted':55,'last_page_preserved':True,'panel_stable_during_reader_mutations':True,'source_pinned_across_tab_switch':True,'scroll_restored':True,'figures_separate_from_reading':True,'saved':True,'image_only_ocr':args.book_images,'all_pages_read_via_cli_fixture':args.book_ai,'state':str(run_dir/'state'),'capture':imported['id']}
            (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
            return
        if args.reader:
            c=capture({},url.replace('article.html','reader-shell.html'))
            assert c['requiredOrigins'] and not c['contentReady'],c
            driver.find_element(By.ID,'authorizeDetection').click()
            driver.set_context('chrome')
            WebDriverWait(driver,10).until(lambda d:d.execute_script('return PopupNotifications.panel.state === "open"'))
            driver.execute_script('PopupNotifications.panel.querySelector("popupnotification").button.click()')
            driver.set_context('content')
            def reader_ready(d):
                result=d.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.get("currentCapture").then(s=>done(s.currentCapture));')
                return result if result and result.get('reader',{}).get('pages') else False
            c=wait.until(reader_ready)
            assert not c['requiredOrigins'],c['detection']
            assert c['detection']['frameReferencesUnmatched']>=1
            assert len(c['reader']['pages'])==4,c['reader']
            assert 'PÁGINA OCULTA' not in c['text']
            assert 'SEGUNDA PÁGINA CARGADA FUERA DE LA PANTALLA' in c['text']
            assert c['images']==[]
            driver.find_element(By.ID,'extractReader').click()
            def extracted(d):
                result=d.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.get(["currentCapture","operation","operationError"]).then(done);')
                if result.get('operationError'):raise AssertionError(result['operationError'])
                return result['currentCapture'] if result['currentCapture'].get('id') and not result.get('operation') else False
            c=WebDriverWait(driver,60).until(extracted)
            assert c['reader']['captured_pages']==4 and len(c['images'])==3
            assert driver.find_element(By.ID,'kind').text=='LECTOR HTML'
            assert not driver.find_element(By.ID,'authorizeDetection').is_displayed()
            assert all(i.is_selected() for i in driver.find_elements(By.CSS_SELECTOR,'#images input'))
            driver.save_screenshot(str(out/'reader.png'))
            driver.find_element(By.CSS_SELECTOR,'#diagnostic summary').click() if driver.find_element(By.ID,'diagnostic').is_displayed() else None
            Select(field('provider')).select_by_value('manual')
            driver.find_element(By.ID,'prepare').click();open_review()
            wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,'#reading figure img'))==3)
            finish_and_return('save',c['source']['tabId'])
            notes=list(vault.rglob('fuente_*.md'));assert len(notes)==1
            assert 'Identidades y permisos' in notes[0].read_text()
            assert len(list(vault.rglob('*.jpg')))==2
            assert len(list(vault.rglob('*.png')))==1
            many=capture({},url.replace('article.html','reader-many.html'))
            assert len(many['reader']['pages'])==10 and not many['images'],many['reader']
            pdf=capture({},url.replace('article.html','reader-pdf.html'))
            if not pdf['documents']:
                wait.until(lambda d:source_script(pdf['source']['tabId'],'document.body.dataset.ready==="yes"'))
                pdf=driver.execute_async_script('const done=arguments[arguments.length-1];browser.runtime.getBackgroundPage().then(async bg=>done(await bg.capture(await browser.tabs.get(arguments[0]))));',pdf['source']['tabId'])
            assert pdf['kind']=='pdf' and pdf['documents'],pdf['documents']
            assert not driver.find_element(By.ID,'noteControls').is_displayed()
            driver.find_element(By.ID,'extractPdf').click()
            WebDriverWait(driver,60).until(lambda d:d.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.get(["currentCapture","operation"]).then(s=>done(s.currentCapture?.id&&s.currentCapture.kind==="pdf"&&!s.operation));'))
            loaded=driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.get("currentCapture").then(s=>done(s.currentCapture));')
            assert '[Página 2]' in loaded['text']
            report={'passed':True,'cross_origin_reader':True,'redirect_does_not_request_access_again':True,'canvas':True,'inline_svg':True,'background_image':True,'hidden_page_excluded':True,'loaded_pages_below_viewport':True,'reader_not_limited_to_eight_pages':True,'original_pdf_found_from_network':True,'original_pdf_extracted':True,'local_attachments':True,'saved':True}
            (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
            return
        c=capture({"kind":"article"})
        assert "MENÚ QUE NO" not in c["text"] and "PUBLICIDAD QUE NO" not in c["text"]
        assert "```" in c["text"] and "| Acción | Objetivo |" in c["text"]
        assert len(c["images"])==1,c["images"]
        assert c['images'][0]['figcaption']=='El ciclo de estudio y recuperación.'
        assert c['images'][0]['alt']=='Diagrama: estudiar, recordar y revisar'
        source_id=c["source"]["tabId"]
        source_script(source_id,'document.querySelector("figure").style.marginTop="1400px";document.body.style.paddingBottom="1400px";document.images[0].style.border="2px solid rgb(1, 2, 3)";window.scrollTo(0,0);true')
        ActionChains(driver).move_to_element(driver.find_element(By.CSS_SELECTOR,".image-pick")).perform()
        wait.until(lambda d:source_script(source_id,'!!document.getElementById("anaco-ob-image-highlight")'))
        wait.until(lambda d:source_script(source_id,'window.scrollY>0'))
        ActionChains(driver).move_to_element(driver.find_element(By.ID,"captureTitle")).perform()
        wait.until(lambda d:not source_script(source_id,'!!document.getElementById("anaco-ob-image-highlight")'))
        assert source_script(source_id,'document.images[0].style.border')=='2px solid rgb(1, 2, 3)'
        driver.find_element(By.CSS_SELECTOR,"#images input").send_keys(Keys.SPACE)
        wait.until(lambda d:source_script(source_id,'!!document.getElementById("anaco-ob-image-highlight")'))
        driver.find_element(By.ID,"intent").click()
        wait.until(lambda d:not source_script(source_id,'!!document.getElementById("anaco-ob-image-highlight")'))
        if args.fresh_permissions:
            # Extraction uses 127.0.0.1; the image uses localhost, which has NOT
            # been granted to this extension. This reproduces first-use prompts.
            c["images"][0]["url"]=c["images"][0]["url"].replace("127.0.0.1","localhost")
            result=driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.set({currentCapture:arguments[0]}).then(()=>done(true));',c)
            assert result
            permitted=driver.execute_async_script('const done=arguments[arguments.length-1];browser.permissions.contains({origins:["http://localhost/*"]}).then(done);')
            assert permitted is False,"The test host must not be pre-authorized"
        if not driver.find_element(By.CSS_SELECTOR,"#images input").is_selected():driver.find_element(By.CSS_SELECTOR,"#images input").click()
        Select(field("provider")).select_by_value("codex" if args.ai else "manual")
        driver.find_element(By.ID,"intent").send_keys("Quiero aprender a repasar mejor.")
        driver.find_element(By.ID,"prepare").click()
        if args.fresh_permissions:
            driver.set_context("chrome")
            WebDriverWait(driver,10).until(lambda d:d.execute_script('return PopupNotifications.panel.state === "open"'))
            prompt=driver.execute_script('const p=PopupNotifications.panel.querySelector("popupnotification");return p?{id:p.id,text:p.textContent,button:!!p.button}:null;')
            (out/"permission-prompt.json").write_text(json.dumps(prompt,ensure_ascii=False,indent=2))
            assert prompt and prompt["button"],prompt
            driver.execute_script('PopupNotifications.panel.querySelector("popupnotification").button.click()')
            driver.set_context("content")
        open_review()
        if not args.ai:
            assert 'El ciclo de estudio y recuperación.' in driver.find_element(By.ID,'markdown').get_attribute('textContent')
            assert 'Pie original del HTML' in driver.find_element(By.ID,'assetList').get_attribute('textContent')
        wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,"#reading figure img"))==1)
        assert driver.find_element(By.CSS_SELECTOR,"#reading figure img").get_attribute("src").startswith("blob:")
        driver.find_element(By.CSS_SELECTOR,"#reading figure img").click()
        assert driver.find_element(By.ID,"imageDialog").get_attribute("open")
        driver.find_element(By.ID,"closeImage").click()
        sanitized=driver.execute_script('''const mount=document.createElement('section');
          AnacoObRender(mount,'# Prueba\\n\\n**Énfasis**\\n\\n[Enlace](javascript:alert(1))\\n\\n<img src="https://tracker.invalid/x" onerror="alert(1)"><script>alert(1)</script>',new Map(),()=>{},'Vault');
          return {heading:mount.querySelector('h1')?.textContent,strong:mount.querySelector('strong')?.textContent,images:mount.querySelectorAll('img').length,scripts:mount.querySelectorAll('script').length,unsafeLinks:[...mount.querySelectorAll('a')].filter(a=>a.getAttribute('href')?.startsWith('javascript:')).length};''')
        assert sanitized=={"heading":"Prueba","strong":"Énfasis","images":0,"scripts":0,"unsafeLinks":0},sanitized
        if args.ai:
            checks=driver.find_elements(By.CSS_SELECTOR,".relation input")
            assert any(x.get_attribute("value").endswith("recuperacion_activa.md") for x in checks)
            assert not any(x.get_attribute("value").endswith("recuperacion_paquetes.md") for x in checks)
            assert all(not x.is_selected() for x in checks)
            for x in checks:
                driver.execute_script("arguments[0].scrollIntoView({block:'center'})",x)
                x.click()
        # Exercise editing and full preview through actual UI controls.
        review_control('edit')
        driver.find_element(By.ID,"body").send_keys("\n\nComentario de validación del usuario.")
        # Reload the review UI: local user edits must survive closing/reopening it.
        driver.refresh()
        wait.until(lambda d:"Comentario de validación" in d.find_element(By.ID,"body").get_attribute("value"))
        if args.ai:
            assert all(x.is_selected() for x in driver.find_elements(By.CSS_SELECTOR,".relation input"))
        review_control('read')
        wait.until(lambda d:"Comentario de validación" in d.find_element(By.ID,"markdown").get_attribute("textContent"))
        driver.save_screenshot(str(out/"review.png"))
        finish_and_return("save",source_id)
        notes=list(vault.rglob("fuente_*.md"));assert len(notes)==1
        assert "Comentario de validación" in notes[0].read_text()
        assert list(vault.rglob("*.png"))
        if not args.ai:
            quote="Aprender es poder recuperar una idea cuando la necesitas."
            q=capture({"kind":"quote","selection":quote})
            Select(field("provider")).select_by_value("manual")
            driver.find_element(By.ID,"prepare").click()
            open_review()
            field("filename").clear();field("filename").send_keys("fuente_2026-10-16_frase_literal.md")
            finish_and_return("save",q["source"]["tabId"])
            assert "> "+quote in next(vault.rglob("*frase_literal.md")).read_text()
            im=capture({"kind":"image","src":url.replace("article.html","diagram.png")})
            Select(field("provider")).select_by_value("manual")
            driver.find_element(By.ID,"prepare").click()
            open_review()
            field("filename").clear();field("filename").send_keys("fuente_2026-10-16_diagrama.md")
            finish_and_return("save",im["source"]["tabId"])
            assert "![[99_Recursos/adjuntos/anaco-ob/" in next(vault.rglob("*diagrama.md")).read_text()
            discarded=capture({"kind":"quote","selection":"Esta captura se descarta, sin escribir una nota."})
            Select(field("provider")).select_by_value("manual")
            driver.find_element(By.ID,"prepare").click();open_review()
            discard_id=driver.execute_script('return new URL(location.href).searchParams.get("capture")')
            before=len(list(vault.rglob("fuente_*.md")))
            finish_and_return("discard",discarded["source"]["tabId"])
            assert len(list(vault.rglob("fuente_*.md")))==before
            assert not any(c["id"]==discard_id for c in message({"type":"native","message":{"action":"status"}})["pending"])
            kept=capture({"kind":"quote","selection":"Borrador que se conserva al volver al artículo."})
            Select(field("provider")).select_by_value("manual")
            driver.find_element(By.ID,"prepare").click();open_review()
            kept_id=driver.execute_script('return new URL(location.href).searchParams.get("capture")')
            finish_and_return("back",kept["source"]["tabId"])
            assert any(c["id"]==kept_id for c in message({"type":"native","message":{"action":"status"}})["pending"])
            driver.find_element(By.ID,"reviewReady").click();open_review()
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.remove(arguments[0]).then(()=>done(true));',kept["source"]["tabId"])
            finish_and_return("discard",None)
        report={"passed":True,"browser":driver.capabilities["browserVersion"],"ai":args.ai,"article":True,"quote":not args.ai,"image":True,"image_hover_highlight":True,"keyboard_highlight":True,"review_tab":True,"local_preview_images":True,"sanitized_markdown":True,"save_returns_to_source":True,"discard_returns_without_note":not args.ai,"native_messaging":True,"fresh_image_permission":args.fresh_permissions,"vault":str(vault),"note_count":len(list(vault.rglob("fuente_*.md"))),"test_host_permission":"http://127.0.0.1/*"}
        if args.media:
            def wait_import(kind):
                WebDriverWait(driver,120).until(lambda d:d.find_element(By.ID,'error').is_displayed() or d.execute_async_script('const done=arguments[arguments.length-1],kind=arguments[0];browser.storage.local.get(["currentCapture","operation"]).then(s=>done(!s.operation&&s.currentCapture?.id&&s.currentCapture.kind===kind));',kind))
                assert not driver.find_element(By.ID,'error').is_displayed(),driver.find_element(By.ID,'error').text
                return driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.get("currentCapture").then(s=>done(s.currentCapture));')
            # Native Firefox PDF viewer rejects content scripts: the production
            # path must detect the PDF before trying to inject into that viewer.
            raw_pdf=capture({},url.replace('article.html','lesson.pdf'))
            assert raw_pdf['kind']=='pdf'
            driver.find_element(By.ID,'extractPdf').click();pdf_capture=wait_import('pdf')
            assert '[Página 2]' in pdf_capture['text'] and len(pdf_capture['images'])==2
            Select(field('provider')).select_by_value('manual')
            driver.find_element(By.ID,'prepare').click();open_review()
            wait.until(lambda d:len(d.find_elements(By.CSS_SELECTOR,'#reading figure img'))==2)
            caption=driver.find_elements(By.CSS_SELECTOR,'.asset-caption')[1]
            caption.clear();caption.send_keys('Diagrama de identidad, política y bucket S3.')
            field('filename').clear();field('filename').send_keys('fuente_2026-10-16_pdf_del_curso.md')
            finish_and_return('save',raw_pdf['source']['tabId'])
            note=next(vault.rglob('*pdf_del_curso.md')).read_text();assert 'Diagrama de identidad, política y bucket S3.' in note
            # Canvas/Moodle-like parent page with an embedded lesson.
            course=capture({},url.replace('article.html','course.html'))
            assert course['videos'] and course['documents']
            wait.until(lambda d:d.find_element(By.ID,'videoControls').is_displayed())
            driver.find_element(By.ID,'extractVideo').click();video=wait_import('video')
            assert '[00:04]' in video['text'] and 'privilegio mínimo' in video['text']
            Select(field('provider')).select_by_value('manual');driver.find_element(By.ID,'prepare').click();open_review()
            field('filename').clear();field('filename').send_keys('fuente_2026-10-16_subtitulos_del_curso.md')
            finish_and_return('save',course['source']['tabId'])
            assert 'formato: "video"' in next(vault.rglob('*subtitulos_del_curso.md')).read_text()
            # The general importer no longer appears on unrelated pages. A local
            # PDF exposes its file chooser because Firefox restricts direct reads.
            assert not driver.find_element(By.ID,'fileImport').is_displayed()
            origin=capture({},(ROOT/'tests/fixtures/lesson.pdf').as_uri())
            details=driver.find_element(By.ID,'importFile').find_element(By.XPATH,'..')
            if not details.get_attribute('open'):details.find_element(By.TAG_NAME,'summary').click()
            driver.find_element(By.ID,'importFile').send_keys(str(ROOT/'tests/fixtures/lesson.pdf'))
            driver.find_element(By.ID,'importButton').click();local=wait_import('pdf')
            assert '[Página 2]' in local['text']
            report['media']={'native_pdf_viewer':True,'pdf_captions':True,'course_iframe_automatic':True,'html_video_subtitles':True,'local_pdf_file_import':True}
        if args.detection:
            def stored_capture():
                return driver.execute_async_script('const done=arguments[arguments.length-1];browser.storage.local.get(["currentCapture","pageContext","operation"]).then(done);')
            def open_active(path):
                tab=driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.create({url:arguments[0],active:true}).then(done);',url.replace('article.html',path))
                result=wait.until(lambda d: (s if s.get('pageContext',{}).get('tabId')==tab['id'] and s['pageContext'].get('status')=='ready' and s.get('currentCapture') else False) if (s:=stored_capture()) else False)
                driver.switch_to.window(panel_handle)
                return tab,result['currentCapture']
            def activate(tab):
                driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.update(arguments[0],{active:true}).then(done);',tab['id'])
                wait.until(lambda d: (s:=stored_capture())['pageContext'].get('tabId')==tab['id'] and s['pageContext'].get('status')=='ready')
                driver.switch_to.window(panel_handle)
                return stored_capture()['currentCapture']
            pdf_tab,pdf=open_active('lesson.pdf')
            assert pdf['documents'] and driver.find_element(By.ID,'pdfControls').is_displayed()
            article_tab,article=open_active('article.html')
            assert article['contentReady'] and not driver.find_element(By.ID,'pdfControls').is_displayed()
            assert not driver.find_element(By.ID,'fileImport').is_displayed()
            empty_tab,empty=open_active('empty.html')
            wait.until(lambda d: d.find_element(By.ID,'error').is_displayed())
            assert 'No se ha encontrado' in driver.find_element(By.ID,'error').text
            assert not driver.find_element(By.ID,'resources').is_displayed()
            assert not driver.find_element(By.ID,'noteControls').is_displayed()
            assert not driver.find_elements(By.ID,'capturePdfActive')
            driver.save_screenshot(str(out/'empty.png'))
            blocked_tab,blocked=open_active('blocked-video.html')
            assert blocked['videos'][0]['extractable'] is False
            assert not driver.find_element(By.ID,'extractVideo').is_displayed()
            assert not driver.find_element(By.ID,'fileImport').is_displayed()
            # A PDF download URL without a suffix is identified by its MIME type.
            mime_tab,mime_pdf=open_active('courses/1/files/22/download')
            assert mime_pdf['kind']=='pdf' and mime_pdf['documents']
            # The embedded provider already has a user session, just as a course
            # player would after login. This visit does not grant host access.
            session_tab=driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.create({url:arguments[0],active:true}).then(done);',url.replace('127.0.0.1','localhost').replace('article.html','session.html'))
            wait.until(lambda d: (s:=stored_capture())['pageContext'].get('tabId')==session_tab['id'] and s['pageContext'].get('status')=='ready')
            driver.switch_to.window(panel_handle)
            nested_tab,nested=open_active('nested-course.html')
            assert nested['requiredOrigins'] and not nested['videos']
            driver.find_element(By.ID,'authorizeDetection').click()
            driver.set_context('chrome')
            WebDriverWait(driver,10).until(lambda d:d.execute_script('return PopupNotifications.panel.state === "open"'))
            driver.execute_script('PopupNotifications.panel.querySelector("popupnotification").button.click()')
            driver.set_context('content')
            wait.until(lambda d: bool(stored_capture()['currentCapture'] and stored_capture()['currentCapture'].get('videos')))
            nested=stored_capture()['currentCapture']
            assert nested['detection']['framesRead']>=3 and nested['videos'][0]['tracks']
            assert driver.find_element(By.ID,'videoControls').is_displayed()
            driver.save_screenshot(str(out/'nested-video.png'))
            driver.find_element(By.ID,'extractVideo').click()
            WebDriverWait(driver,60).until(lambda d: (s:=stored_capture())['currentCapture'].get('id') and not s.get('operation'))
            assert 'privilegio mínimo' in stored_capture()['currentCapture']['text']
            assert activate(pdf_tab)['kind']=='pdf'
            assert activate(article_tab)['contentReady']
            dynamic_tab,dynamic=open_active('dynamic-video.html')
            driver.execute_async_script('const done=arguments[arguments.length-1];browser.tabs.update(arguments[0],{active:true}).then(done);',dynamic_tab['id'])
            wait.until(lambda d: any(v['url'].endswith('stream.m3u8') for v in (stored_capture()['currentCapture'] or {}).get('videos',[])))
            driver.switch_to.window(panel_handle)
            wait.until(lambda d: d.find_element(By.ID,'extractVideo').is_displayed())
            driver.find_element(By.ID,'extractVideo').click()
            WebDriverWait(driver,120).until(lambda d: (s:=stored_capture())['currentCapture'].get('id') and not s.get('operation'))
            assert 'Whisper' in stored_capture()['currentCapture']['media']['method']
            panel_handle=open_manual_importer()
            details=driver.find_element(By.ID,'importFile').find_element(By.XPATH,'..')
            details.find_element(By.TAG_NAME,'summary').click()
            driver.find_element(By.ID,'importFile').send_keys(str(ROOT/'tests/fixtures/lesson.vtt'))
            driver.find_element(By.ID,'importButton').click()
            WebDriverWait(driver,30).until(lambda d: (s:=stored_capture())['currentCapture'].get('url','').startswith('local-file:') and not s.get('operation'))
            assert 'privilegio mínimo' in stored_capture()['currentCapture']['text']
            assert driver.find_element(By.ID,'prepare').is_displayed()
            report['detection']={'active_tab_updates':True,'pdf_controls_scoped_to_page':True,'empty_page_error':True,
                'blocked_video_error':True,'pdf_without_extension':True,'nested_cross_origin_permission':True,
                'nested_subtitles_with_session':True,'dynamic_blob_to_hls':True,'hls_session_download_and_asr':True,'manual_import_separate':True}
        report['note_count']=len(list(vault.rglob('fuente_*.md')))
        (out/"report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
    except Exception:
        if driver:
            driver.save_screenshot(str(out/"failure.png"))
            (out/"failure.html").write_text(driver.page_source)
            try:
                (out/"failure-state.json").write_text(json.dumps(driver.execute_async_script('const done=arguments[arguments.length-1];Promise.all([browser.storage.local.get(["currentCapture","pageContext","operationError","activeWork"]),browser.tabs.query({active:true}),browser.tabs.getCurrent()]).then(([state,active,current])=>done({...state,active,current,visibility:document.visibilityState,filename:document.getElementById("filename")?.value,saveDisabled:document.getElementById("save")?.disabled,previewState:document.getElementById("previewState")?.textContent}));'),ensure_ascii=False,indent=2))
            except Exception:pass
        raise
    finally:
        for path, data in backups.items():
            if data is None:path.unlink(missing_ok=True)
            else:path.write_bytes(data)
        try:
            if driver:driver.quit()
        finally:
            if server:server.shutdown()


if __name__ == "__main__":main()
