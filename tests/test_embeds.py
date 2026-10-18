import base64
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
from core import UserError
from media import Media
import test_core as core_tests

MP4=b'\x00\x00\x00\x18ftypmp42'+b'\x00'*64
LIB=b'window.gsap={version:"3"};'
RESULT='''<!DOCTYPE html><html><head><title>Sunny</title>
<script src="https://cpwebassets.codepen.io/assets/common/stopExecutionOnTimeout-1.js"></script>
<link rel="icon" href="https://cpwebassets.codepen.io/favicon.ico"><style>body{margin:0}</style></head>
<body><canvas id="eggs"></canvas><script src="https://unpkg.com/gsap@3/dist/gsap.min.js"></script>
<script>for(let i=0;i<3;i++){if(window.CP.shouldStopExecution(0))break;}window.CP.exitedLoop(0);</script></body></html>'''


class EmbedsTest(unittest.TestCase):
    setUp=core_tests.CoreTest.setUp
    tearDown=core_tests.CoreTest.tearDown

    def asset(self,name,raw):
        media=Media(self.app);upload=media.begin({'name':name,'size':len(raw),'purpose':'asset'})['upload']
        media.chunk({'upload':upload,'offset':0,'data':base64.b64encode(raw).decode()})
        return media.finish_asset({'upload':upload})['asset']

    def capture(self,embeds,text=None):
        text=text or 'Intro del artículo sobre shaders y demos interactivas en la web.\n\n{{recurso:0}}\n\nTexto entre recursos que explica la técnica.\n\n{{recurso:1}}\n\n{{recurso:2}}\n\nCierre.'
        c=self.app.stage({'kind':'article','url':'https://tympanus.net/codrops/2026/10/16/ksenia-kondrashova/','title':'Ksenia','text':text,'embeds':embeds})
        return c,self.app.draft(c['id'],provider='manual')

    def embeds(self):
        clip=self.asset('globe.mp4',MP4);page=self.asset('index.html',RESULT.encode());lib=self.asset('gsap.min.js',LIB)
        return [
            {'type':'tweet','selected':True,'url':'https://twitter.com/uuuuuulala/status/1803039502136426656','author':'Ksenia Kondrashova (@uuuuuulala) June 18, 2024','text':'In 2022 I published a tutorial.\nPackaging people, call me!'},
            {'type':'clip','selected':True,'url':'https://tympanus.net/clips/globe1-optimized.mp4','title':'globe1-optimized.mp4','caption':'Un globo girando','asset':clip,'size':len(MP4)},
            {'type':'pen','selected':True,'url':'https://codepen.io/ksenia-k/pen/rNXPZRN','user':'ksenia-k','slug':'rNXPZRN','title':'Interactive sunny-side pattern',
             'code':{'html':'<canvas id="eggs"></canvas>','css':'body{margin:0}','js':'const canvasEl=document.querySelector("#eggs");'},'code_source':'source',
             'demo':{'page':page,'libs':[{'url':'https://unpkg.com/gsap@3/dist/gsap.min.js','asset':lib}]}},
        ]

    def test_resources_appear_in_place_with_local_files(self):
        c,_=self.capture(self.embeds())
        result=self.app.save(c['id'],{});note=Path(result['path']).read_text()
        self.assertNotIn('{{recurso',note)
        self.assertLess(note.index('![](https://twitter.com/uuuuuulala/status/1803039502136426656)'),note.index('Texto entre recursos'))
        self.assertIn('> Packaging people, call me!',note)
        clip=next(self.vault.rglob('*.mp4'));self.assertEqual(clip.read_bytes(),MP4)
        self.assertIn('![['+clip.relative_to(self.vault).as_posix()+']]',note)
        page=next(self.vault.rglob('index.html'));html=page.read_text()
        self.assertIn('```html-preview\n[['+page.relative_to(self.vault).as_posix()+']]',note)
        self.assertIn('https://codepen.io/ksenia-k/pen/rNXPZRN',note)
        self.assertIn('> const canvasEl=document.querySelector("#eggs");',note)
        # Offline copy: local library, CodePen loop guard stubbed, no CodePen runtime fetch.
        self.assertNotIn('unpkg.com',html);self.assertNotIn('stopExecutionOnTimeout',html);self.assertIn('window.CP=',html)
        lib=next(p for p in page.parent.iterdir() if p.suffix=='.js');self.assertEqual(lib.read_bytes(),LIB);self.assertIn('src="'+lib.name+'"',html)

    def test_unselected_resources_leave_no_trace_and_unplaced_ones_are_kept(self):
        values=self.embeds();values[0]['selected']=False
        c,_=self.capture(values,text='Texto suficiente del artículo para generar la nota de prueba.\n\n{{recurso:0}}\n\n{{recurso:2}}')
        note=self.app.preview(c['id'],{})['markdown']
        self.assertNotIn('twitter.com',note)
        # The clip token was not placed by the draft; it stays in the note, after the body.
        self.assertIn('## Recursos de la fuente',note);self.assertIn('.mp4]]',note.split('## Recursos de la fuente')[1])
        self.assertEqual(note.count('html-preview'),1)

    def test_pen_without_offline_copy_keeps_code_and_link(self):
        values=self.embeds();values[2].pop('demo')
        c,_=self.capture(values)
        note=self.app.preview(c['id'],{})['markdown']
        self.assertNotIn('html-preview',note);self.assertIn('Sin copia local',note);self.assertIn('Ver en CodePen',note)

    def test_invalid_resources_are_rejected_before_storage(self):
        bad=[{'type':'script','url':'https://example.org'},{'type':'tweet','url':'javascript:alert(1)'},{'type':'clip','url':'https://a.example/x.mp4','asset':'../../etc/passwd'},{'type':'clip','url':'https://a.example/x.mp4','asset':'0'*64+'.mp4'}]
        for value in bad:
            with self.assertRaises(UserError,msg=value):self.capture([{**value,'selected':True}])

    def test_demo_file_names_cannot_leave_their_folder(self):
        values=self.embeds();values[2]['demo']['libs'][0]['name']='../../00_Sistema/x.js'
        with self.assertRaises(UserError):self.capture(values)

    def test_asset_upload_accepts_only_known_resource_types(self):
        with self.assertRaises(UserError):Media(self.app).begin({'name':'payload.exe','size':10,'purpose':'asset'})
        with self.assertRaises(UserError):Media(self.app).begin({'name':'huge.js','size':20_000_000,'purpose':'asset'})

    def test_capture_without_resources_renders_as_before(self):
        c=self.app.stage({'kind':'article','url':'https://example.org/lesson','title':'Lección','text':'La recuperación activa mejora el aprendizaje. Repetir pruebas ayuda a recordar.'})
        self.app.draft(c['id'],provider='manual')
        note=self.app.preview(c['id'],{})['markdown']
        self.assertNotIn('Recursos de la fuente',note);self.assertNotIn('embeds',self.app.load(c['id']))


if __name__=='__main__':
    unittest.main()
