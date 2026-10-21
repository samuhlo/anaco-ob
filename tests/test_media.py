import base64
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
from core import UserError
from media import Media,subtitles,page_range
from media_fixtures import make_pdf
import test_core as core_tests
PNG=core_tests.PNG


class MediaTest(unittest.TestCase):
    setUp=core_tests.CoreTest.setUp
    tearDown=core_tests.CoreTest.tearDown
    capture=core_tests.CoreTest.capture
    prepared=core_tests.CoreTest.prepared

    def upload(self,path,pages=''):
        media=Media(self.app);raw=path.read_bytes();identifier=media.begin({'name':path.name,'size':len(raw)})['upload']
        media.chunk({'upload':identifier,'offset':0,'data':base64.b64encode(raw).decode()})
        return media.finish({'upload':identifier,'pages':pages})

    def test_pdf_text_pages_and_rendered_visuals(self):
        pdf=make_pdf(self.root/'pdf')
        c=self.upload(pdf)
        self.assertEqual(c['kind'],'pdf');self.assertIn('[Página 2]',c['text']);self.assertIn('Least privilege',c['text'])
        self.assertEqual(c['media']['total_pages'],2);self.assertEqual(len(c['images']),2)
        self.app.draft(c['id'],provider='manual')
        saved=self.app.save(c['id'],{})
        note=Path(saved['path']).read_text();self.assertIn('formato: "documento"',note);self.assertNotIn('fuente_url:',note)
        self.assertEqual(len(list(self.vault.rglob('*.jpg'))),2)

    def test_pdf_range_has_explicit_scope(self):
        c=self.upload(make_pdf(self.root/'pdf'),'2')
        self.assertEqual(c['media']['pages'],[2]);self.assertTrue(c['warnings']);self.assertNotIn('[Página 1]',c['text'])

    def test_pdf_rejects_html_login_response(self):
        fake=self.root/'login.pdf';fake.write_bytes(b'<html>Login required</html>')
        with self.assertRaises(UserError):self.upload(fake)

    def test_subtitle_timing_and_rolling_duplicates(self):
        segments=subtitles('WEBVTT\n\n00:00.000 --> 00:02.000\nAWS IAM manages\n\n00:02.000 --> 00:04.000\nAWS IAM manages identities\n\n00:04.000 --> 00:05.000\nidentities\n')
        self.assertEqual([s['text'] for s in segments],['AWS IAM manages','identities'])
        self.assertEqual(segments[1]['start'],2)

    def test_srt_import_is_video_with_timestamps(self):
        path=self.root/'lesson.srt';path.write_text('1\n00:00:01,250 --> 00:00:03,000\nUna política autoriza acciones.\n\n2\n00:00:05,000 --> 00:00:08,000\nAplicar privilegio mínimo.\n')
        c=self.upload(path);self.assertEqual(c['kind'],'video');self.assertIn('[00:01]',c['text'])
        self.app.draft(c['id'],provider='manual');self.assertIn('formato: "video"',self.app.preview(c['id'],{})['markdown'])

    def test_upload_size_offset_and_id_validation(self):
        m=Media(self.app)
        for size in (0,100_000_001,True):
            with self.assertRaises(UserError):m.begin({'name':'x.pdf','size':size})
        identifier=m.begin({'name':'x.pdf','size':10})['upload']
        with self.assertRaises(UserError):m.chunk({'upload':identifier,'offset':1,'data':'YQ=='})
        with self.assertRaises(UserError):m.finish({'upload':identifier})
        with self.assertRaises(UserError):m.upload_dir('../escape')

    def test_ranges_validate_bounds(self):
        self.assertEqual(page_range('1-3,5',8,5),[1,2,3,5])
        for value in ('0','3-1','9','1-8','x'):
            with self.assertRaises(UserError):page_range(value,8,5)

    def test_caption_reaches_markdown_and_recommended_images(self):
        c=self.capture(kind='pdf',images=[{'data':base64.b64encode(PNG).decode(),'alt':''}])
        description='Diagrama con identidad, política de permisos y recurso de AWS conectados mediante flechas.'
        answer={'title':'Permisos','context':'Estudio','body':'Resumen.','folder':'02_Cerebro/Tech_&_Codigo','tags':['aws'],'relations':[],
                'image_captions':[{'index':0,'description':description,'useful':True}],'_model':'gpt-6.1-sol'}
        with patch.object(self.app,'codex_generate',return_value=answer):draft=self.app.draft(c['id'],provider='codex')
        self.assertEqual(draft['draft']['model'],'gpt-6.1-sol')
        self.assertEqual(self.app.load(c['id'])['images'][0]['caption'],description)
        self.assertIn(description,self.app.preview(c['id'],{})['markdown'])
        self.assertIn('Descripción editada',self.app.preview(c['id'],{'captions':{'0':'Descripción editada'}})['markdown'])
        self.assertNotIn('![[',self.app.preview(c['id'],{'images':[]})['markdown'])

    def test_images_are_attached_to_vision_without_base64_prompt(self):
        c=self.capture(images=[{'data':base64.b64encode(PNG).decode(),'alt':'','thumbnail':'data:image/jpeg;base64,PRIVATE'}])
        stored=self.app.load(c['id']);stored['selected_images']=[0]
        def fake(command,**kwargs):
            self.assertIn('--image',command);self.assertEqual(command[command.index('--model')+1],'gpt-6.1-sol')
            self.assertNotIn('base64,PRIVATE',kwargs['input'])
            answer=Path(command[command.index('--output-last-message')+1]);answer.write_text('{}')
            class Result:returncode=0
            return Result()
        with patch('core.subprocess.run',side_effect=fake):result=self.app.codex_generate(stored,[],self.app.folders())
        self.assertEqual(result['_model'],'gpt-6.1-sol')

    def test_missing_visual_description_cannot_silently_publish_placeholder(self):
        c=self.capture(images=[{'data':base64.b64encode(PNG).decode(),'alt':''}])
        answer={'title':'Imagen','context':'Contexto','body':'Resumen','folder':'02_Cerebro/Tech_&_Codigo','tags':[],'relations':[],'image_captions':[]}
        with patch.object(self.app,'codex_generate',return_value=answer):
            with self.assertRaises(UserError):self.app.draft(c['id'],provider='codex')
        self.assertEqual(self.app.load(c['id'])['status'],'pending')


class YouTubeTimesTest(unittest.TestCase):
    setUp=core_tests.CoreTest.setUp
    tearDown=core_tests.CoreTest.tearDown
    VTT=('WEBVTT\n\n00:00:05.000 --> 00:00:07.000\nBienvenidos al programa.\n\n'
         '00:12:34.000 --> 00:12:38.000\nHablemos de inflación.\n\n01:02:03.000 --> 01:02:05.000\nUna última idea.\n')

    def youtube(self,meta=None):
        meta={'title':'Entrevista de economía','duration':3800,'channel':'Tengo un Plan',
              'chapters':[{'start_time':0,'end_time':700,'title':'Presentación'},{'start_time':700,'end_time':3800,'title':'Inflación y ahorro'}],
              'subtitles':{'es':[{'ext':'vtt','url':'https://example.org/subs.vtt'}]},**(meta or {})}
        response=unittest.mock.MagicMock();response.__enter__.return_value.read.return_value=self.VTT.encode()
        with patch.object(Media,'run',return_value=json.dumps(meta).encode()),patch('media.urlopen',return_value=response):
            return Media(self.app).video_url({'url':'https://www.youtube.com/watch?v=abcdefghijk&list=PL1'})

    def test_chapters_are_kept_in_the_capture_and_marked_in_the_transcript(self):
        c=self.youtube()
        self.assertEqual(c['author'],'Tengo un Plan')
        self.assertEqual(c['media']['chapters'],[{'start':0,'title':'Presentación'},{'start':700,'title':'Inflación y ahorro'}])
        lines=c['text'].splitlines()
        self.assertLess(lines.index('[Capítulo 00:00] Presentación'),lines.index('[00:05] Bienvenidos al programa.'))
        self.assertLess(lines.index('[Capítulo 11:40] Inflación y ahorro'),lines.index('[12:34] Hablemos de inflación.'))

    def test_note_times_open_the_video_at_that_second(self):
        c=self.youtube();self.app.draft(c['id'],provider='manual')
        body='## Temas\n\n- [12:34] Inflación.\n- [1:02:03] Cierre.\n- [2:00:00] Fuera del vídeo.\n- [12:34](https://otra.web) Ya enlazado.'
        markdown=self.app.preview(c['id'],{'body':body})['markdown']
        self.assertIn('- [12:34](https://www.youtube.com/watch?v=abcdefghijk&t=754s) Inflación.',markdown)
        self.assertIn('- [1:02:03](https://www.youtube.com/watch?v=abcdefghijk&t=3723s) Cierre.',markdown)
        self.assertIn('- [2:00:00] Fuera del vídeo.',markdown)
        self.assertIn('- [12:34](https://otra.web) Ya enlazado.',markdown)
        markdown=self.app.preview(c['id'],{'body':'En [49:00–55:41] habla de fondos y en [12:34 - 13:00] de ahorro.'})['markdown']
        self.assertIn('En [49:00–55:41](https://www.youtube.com/watch?v=abcdefghijk&t=2940s) habla',markdown)
        self.assertIn('en [12:34 - 13:00](https://www.youtube.com/watch?v=abcdefghijk&t=754s) de ahorro',markdown)

    def test_a_relation_whose_evidence_has_a_time_still_saves(self):
        c=self.youtube();self.app.draft(c['id'],provider='manual')
        path='02_Cerebro/Tech_&_Codigo/nota_ahorro.md';(self.vault/path).write_text('# Ahorro\n\n## Inflación\n\nLa inflación reduce el poder adquisitivo de los ahorros guardados en efectivo.')
        stored=self.app.load(c['id']);evidence='En [12:34] se explica que la inflación reduce el valor del efectivo ahorrado.'
        stored['draft']['body']='## Temas\n\n'+evidence
        stored['draft']['relations']=[{'path':path,'reason':'Explica el mecanismo de la inflación sobre el ahorro.','kind':'explica','source_evidence':evidence,
                                       'note_evidence':'La inflación reduce el poder adquisitivo de los ahorros','evidence_origin':'note','accepted':False}]
        self.app.store(stored)
        markdown=self.app.preview(c['id'],{'relations':[path]})['markdown']
        self.assertIn('En [12:34](https://www.youtube.com/watch?v=abcdefghijk&t=754s) se explica',markdown)
        self.assertIn('[[02_Cerebro/Tech_&_Codigo/nota_ahorro#Inflación]]',markdown)

    def test_local_subtitles_keep_plain_times(self):
        path=self.root/'lesson.srt';path.write_text('1\n00:00:01,250 --> 00:00:03,000\nUna política autoriza acciones.\n')
        c=MediaTest.upload(self,path);self.app.draft(c['id'],provider='manual')
        markdown=self.app.preview(c['id'],{})['markdown']
        self.assertIn('[00:01] Una política',markdown);self.assertNotIn('&t=',markdown)
