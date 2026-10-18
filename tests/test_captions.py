import base64
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'native'))
from captions import html_caption,filename_hint,informative
import test_core as core_tests


class CaptionTest(unittest.TestCase):
    setUp=core_tests.CoreTest.setUp
    tearDown=core_tests.CoreTest.tearDown
    capture=core_tests.CoreTest.capture

    def image(self,**values):return {'data':base64.b64encode(core_tests.PNG).decode(),'alt':'',**values}

    def test_visible_caption_precedes_alt_and_is_preserved_without_vision(self):
        text='Estructura de permisos IAM y acceso a recursos de AWS.'
        c=self.app.load(self.capture(images=[self.image(figcaption=text,alt='Descripción alternativa del esquema de AWS')])['id'])
        self.assertEqual(self.app.prepare_captions(c),[])
        self.assertEqual(c['images'][0]['caption'],text)
        self.assertEqual(c['images'][0]['caption_source'],'figcaption')
        self.assertNotIn('caption_model',c['images'][0])

    def test_accessibility_alt_and_title_fallbacks(self):
        for key in ('aria_description','alt','aria_label','title'):
            text='Diagrama de los permisos de una identidad de AWS.'
            self.assertEqual(html_caption(self.image(**{key:text})),(text,key))

    def test_generic_labels_do_not_suppress_visual_fallback(self):
        for label in ('Imagen 1','Screenshot','Página 2 del PDF','imagen de la fuente descripción pendiente','a_photo.png'):
            self.assertEqual(informative(label),'',label)
        c=self.app.load(self.capture(images=[self.image(alt='Imagen 1')])['id'])
        self.assertEqual(self.app.prepare_captions(c),[0])

    def test_descriptive_filename_is_explicit_hint_and_hashes_are_rejected(self):
        hint=filename_hint({'url':'https://example.org/aws-iam-permission-flow-1200x800.png'})
        self.assertEqual(hint,'Nombre del archivo: aws iam permission flow.')
        for name in ('screenshot-2026-10-16.png','8a987bfacdd223cbb8c1.jpg','image-01.png'):
            self.assertEqual(filename_hint({'url':'https://example.org/'+name}),'' )
        c=self.app.load(self.capture(images=[self.image(url='https://example.org/aws-iam-permission-flow.png')])['id'])
        self.assertEqual(self.app.prepare_captions(c),[])
        self.assertEqual(c['images'][0]['caption_source'],'filename')

    def test_html_only_uses_text_model_and_has_no_image_attachments(self):
        c=self.app.load(self.capture(images=[self.image(figcaption='Diagrama del flujo de permisos entre identidades y recursos.')])['id'])
        def fake(command,**kwargs):
            self.assertNotIn('--image',command)
            self.assertEqual(command[command.index('--model')+1],'gpt-6-luna')
            Path(command[command.index('--output-last-message')+1]).write_text('{}')
            class Result:returncode=0
            return Result()
        with patch('core.subprocess.run',side_effect=fake):result=self.app.codex_generate(c,[],self.app.folders())
        self.assertEqual(result['_model'],'gpt-6-luna')

    def test_mixed_capture_attaches_only_image_without_description(self):
        c=self.app.load(self.capture(images=[self.image(alt='Esquema de las conexiones de red en una VPC.'),self.image()])['id'])
        def fake(command,**kwargs):
            files=[command[i+1] for i,item in enumerate(command) if item=='--image']
            self.assertEqual(len(files),1);self.assertTrue(files[0].endswith('image-1.png'))
            self.assertIn('"vision_images": [1]',kwargs['input'])
            Path(command[command.index('--output-last-message')+1]).write_text('{}')
            class Result:returncode=0
            return Result()
        with patch('core.subprocess.run',side_effect=fake):self.app.codex_generate(c,[],self.app.folders())

    def test_visual_caption_reused_across_captures_without_new_analysis(self):
        first=self.capture(images=[self.image()])
        answer={'title':'Diagrama','context':'Contexto','body':'Resumen.','folder':'02_Cerebro/Tech_&_Codigo','tags':[],'relations':[],
                'image_captions':[{'index':0,'description':'Tres bloques conectados que representan identidades, políticas y recursos.','useful':True}],'_model':'gpt-6.1-sol'}
        with patch.object(self.app,'codex_generate',return_value=answer):self.app.draft(first['id'],provider='codex')
        second=self.app.load(self.capture(url='https://example.org/another-article',images=[self.image()])['id'])
        self.assertEqual(self.app.prepare_captions(second),[])
        self.assertEqual(second['images'][0]['caption_source'],'vision_cache')
        self.assertIn('Tres bloques',second['images'][0]['caption'])

    def test_source_only_never_attaches_even_pdf_pages(self):
        self.app.set_config({'vision_policy':'metadata'})
        c=self.app.load(self.capture(kind='pdf',images=[self.image()])['id'])
        self.assertEqual(self.app.prepare_captions(c),[])

    def test_forced_vision_and_pdf_content_analysis_are_preserved(self):
        image=self.image(alt='Descripción suficientemente detallada para evitar analizar una imagen normal.')
        c=self.app.load(self.capture(images=[image])['id']);self.assertEqual(self.app.prepare_captions(c),[])
        self.app.set_config({'vision_policy':'always'});self.assertEqual(self.app.prepare_captions(c),[0])
        self.app.set_config({'vision_policy':'auto'})
        c['kind']='pdf';self.assertEqual(self.app.prepare_captions(c),[0])
        c['kind']='video';self.assertEqual(self.app.prepare_captions(c),[0])

    def test_reader_page_requires_content_analysis_beyond_its_label(self):
        c=self.app.load(self.capture(reader={'scope':'loaded'},images=[self.image(alt='Página del libro de conceptos de cloud',visual_page=True)])['id'])
        self.assertEqual(c['reader']['scope'],'loaded')
        self.assertEqual(self.app.prepare_captions(c),[0])
        self.app.set_config({'vision_policy':'metadata'})
        self.assertEqual(self.app.prepare_captions(c),[])
