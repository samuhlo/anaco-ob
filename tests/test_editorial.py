import copy
import base64
import hashlib
from unittest.mock import patch
import test_core as base
from core import UserError, write_new_atomic
from editorial import Editorial


class EditorialTest(base.unittest.TestCase):
    setUp=base.CoreTest.setUp
    tearDown=base.CoreTest.tearDown

    def collection(self):
        self.app.set_config({'note_structure':'linked'})
        evidence='Una identidad solicita acceso y la política decide qué acciones puede realizar sobre el recurso.'
        c=self.app.stage({'url':'https://example.org/book','title':'Manual de permisos','kind':'article','text':evidence})
        stored=self.app.load(c['id']);stored['media']={'type':'reader','pages':[1,2],'total_pages':2};self.app.store(stored)
        folder='02_Cerebro/Tech_&_Codigo'
        common={'context':'Estudio de permisos','folder':folder,'tags':['cloud'],'relations':[],'images':[],'source_evidence':evidence,'links':[]}
        result={'title':'Permisos: síntesis y mapa','context':'Visión conjunta','body':'## Síntesis\n\nUna identidad necesita permisos para acceder a un recurso.',
                'folder':folder,'tags':['cloud'],'relations':[],'image_captions':[],'note_type':'fuente_externa','strategy':'collection','source_format':'libro',
                'rationale':'Dos apartados distintos: quién solicita acceso y cómo se decide el permiso.',
                'notes':[{**common,'id':'identidad','title':'Identidades y recursos','note_type':'referencia_tecnica','body':'## Quién solicita acceso\n\nLa identidad representa al solicitante.','pages':[1],
                          'links':[{'id':'politicas','reason':'La política determina los permisos de esa identidad.'}]},
                         {**common,'id':'politicas','title':'Decidir permisos con políticas','note_type':'nota_atomica','body':'## Cómo se decide\n\nLa política permite o deniega acciones.','pages':[2]}]}
        return c,result

    def prepared(self):
        c,result=self.collection()
        with patch.object(self.app,'codex_generate',return_value=result):self.app.draft(c['id'],provider='codex')
        return self.app.load(c['id'])

    def test_collection_has_real_reciprocal_links_and_typed_frontmatter(self):
        c=self.prepared();editor=Editorial(self.app)
        preview=self.app.preview(c['id'],{})
        children=c['bundle']['notes']
        for child in children:self.assertIn('[['+child['folder']+'/'+child['filename'][:-3]+'|',preview['markdown'])
        child=self.app.preview(c['id'],{'active_note':'identidad'})
        self.assertIn('tipo: "referencia_tecnica"',child['markdown'])
        self.assertIn('[['+c['draft']['folder']+'/'+c['draft']['filename'][:-3]+'|',child['markdown'])
        self.assertNotIn('IDEAS CLAVE',child['markdown'])
        saved=self.app.save(c['id'],{})
        self.assertEqual(saved['count'],3)
        for path in saved['paths']:self.assertTrue((self.vault/path).is_file())

    def test_renames_and_exclusions_update_links_before_saving(self):
        c=self.prepared()
        fields={'notes':{'identidad':{'filename':'nota_identidad_revisada.md'}},'selected_notes':['source','identidad'],'active_note':'identidad'}
        child=self.app.preview(c['id'],fields)
        self.assertNotIn('nota_decidir_permisos',child['markdown'])
        root=self.app.preview(c['id'],{**fields,'active_note':'source'})
        self.assertIn('nota_identidad_revisada',root['markdown'])
        self.assertNotIn('nota_decidir_permisos',root['markdown'])
        self.assertEqual(self.app.save(c['id'],fields)['count'],2)

    def test_adaptive_notes_keep_scope_and_acquisition_method_in_the_source_footer(self):
        c=self.prepared();c['media'].update(coverage='2/2 páginas leídas por lotes',method='Texto HTML y OCR local',reading_models=['gpt-6-luna']);self.app.store(c)
        markdown=self.app.preview(c['id'],{})['markdown']
        self.assertIn('2/2 páginas leídas por lotes',markdown)
        self.assertIn('Texto HTML y OCR local',markdown)
        self.assertIn('Modelos: gpt-6-luna',markdown)
        self.assertNotIn('FICHA RAPIDA',markdown)

    def test_figure_assigned_to_a_section_uses_its_caption_and_is_not_repeated_in_the_index(self):
        c,result=self.collection();stored=self.app.load(c['id'])
        stored['images']=[{'data':base64.b64encode(base.PNG).decode(),'alt':'Diagrama de identidad, política y recurso','page':1}];self.app.store(stored)
        result['notes'][0]['images']=[0]
        with patch.object(self.app,'codex_generate',return_value=result):self.app.draft(c['id'],provider='codex')
        self.assertNotIn('![[',self.app.preview(c['id'],{})['markdown'])
        section=self.app.preview(c['id'],{'active_note':'identidad'})['markdown']
        self.assertIn('![[',section);self.assertIn('Diagrama de identidad, política y recurso',section)
        self.app.save(c['id'],{})
        self.assertEqual(len(list(self.vault.rglob('*.png'))),1)

    def test_existing_file_prevents_all_writes(self):
        c=self.prepared();note=c['bundle']['notes'][1]
        target=self.vault/note['folder']/note['filename'];target.write_text('APUNTES EXISTENTES')
        with self.assertRaises(UserError):self.app.save(c['id'],{})
        self.assertEqual(target.read_text(),'APUNTES EXISTENTES')
        self.assertFalse((self.vault/c['draft']['folder']/c['draft']['filename']).exists())

    def test_failure_rolls_back_only_the_notes_created_by_this_attempt(self):
        c=self.prepared();calls=[]
        def fail_second(path,raw):
            calls.append(path)
            if len(calls)==2:raise OSError('Interrupted filesystem')
            return write_new_atomic(path,raw)
        with patch('editorial.write_new_atomic',side_effect=fail_second):
            with self.assertRaises(OSError):self.app.save(c['id'],{})
        for d in [c['draft'],*c['bundle']['notes']]:self.assertFalse((self.vault/d['folder']/d['filename']).exists())
        self.assertEqual(self.app.save(c['id'],{})['count'],3)

    def test_interrupted_publication_can_resume_without_overwriting(self):
        c=self.prepared();rendered,selected,_=Editorial(self.app).render_all(c,{})
        c['save_intent']={'hashes':{r['relative']:hashlib.sha256(r['markdown'].encode()).hexdigest() for r in rendered.values()}};self.app.store(c)
        first=rendered[selected[0]];target=self.vault/first['relative'];target.write_text(first['markdown'])
        before=target.stat().st_mtime_ns
        self.assertEqual(self.app.save(c['id'],{})['count'],3)
        self.assertEqual(target.stat().st_mtime_ns,before)

    def test_invalid_page_cannot_create_an_unverified_collection(self):
        c,result=self.collection();result['notes'][0]['pages']=[99]
        with patch.object(self.app,'codex_generate',return_value=result):
            with self.assertRaises(UserError):self.app.draft(c['id'],provider='codex')
        self.assertNotIn('bundle',self.app.load(c['id']))

    def test_unresolved_optional_links_are_omitted_without_losing_the_collection(self):
        c,result=self.collection()
        result['notes'][0]['links'] += [{'id':'inventado','reason':'Esta nota no está en la propuesta.'},
                                       {'id':'identidad','reason':'Un enlace a sí misma no aporta contexto.'}]
        with patch.object(self.app,'codex_generate',return_value=result):self.app.draft(c['id'],provider='codex')
        stored=self.app.load(c['id'])
        self.assertEqual([v['id'] for v in stored['bundle']['notes'][0]['links']],['politicas'])
        rendered=self.app.preview(c['id'],{'active_note':'identidad'})['markdown']
        self.assertNotIn('inventado',rendered)
        self.assertIn('Síntesis y mapa de esta fuente',rendered)

    def test_mental_model_is_classified_as_knowledge_and_not_a_generic_article(self):
        text='Cambiar una creencia requiere buscar evidencia que pueda refutarla.'
        c=self.app.stage({'url':'https://example.org/beliefs','title':'Refutación','text':text})
        result={'title':'Buscar evidencia que refute una creencia','context':'Pensar con evidencia','body':'## Mecanismo\n\nBuscar contraejemplos permite revisar una creencia.','folder':'02_Cerebro/Modelos_Mentales','tags':['razonamiento'],'relations':[],
                'image_captions':[],'note_type':'modelo_mental','strategy':'concept','source_format':'articulo','rationale':'Explica un mecanismo de razonamiento reutilizable.','notes':[]}
        with patch.object(self.app,'codex_generate',return_value=result):self.app.draft(c['id'],provider='codex')
        preview=self.app.preview(c['id'],{})
        self.assertIn('tipo: "modelo_mental"',preview['markdown'])
        self.assertTrue(preview['relative'].split('/')[-1].startswith('nota_'))
        self.assertNotIn('FICHA RAPIDA',preview['markdown'])
        self.assertNotIn('QUE PUEDO APRENDER',preview['markdown'])

    def test_class_sections_use_apunte_and_the_existing_class_metadata(self):
        c,result=self.collection();folder='07_Clases/01_Curso/01_Tema'
        result['folder']=folder;result['note_type']='resumen'
        for child in result['notes']:child.update(folder=folder,note_type='apunte')
        with patch.object(self.app,'codex_generate',return_value=result):self.app.draft(c['id'],provider='codex')
        preview=self.app.preview(c['id'],{'active_note':'identidad'})
        self.assertIn('tipo: "apunte"',preview['markdown'])
        self.assertIn('curso: "Curso"',preview['markdown'])
        self.assertIn('/apunte_',preview['relative'])

    def test_new_collection_can_derive_from_a_previously_saved_source(self):
        c,result=self.collection()
        self.app.draft(c['id'],provider='manual');first=self.app.save(c['id'],{})
        fresh=self.app.stage({'url':'https://example.org/book','title':'Manual de permisos','kind':'article','text':self.app.load(c['id'])['text']})
        stored=self.app.load(fresh['id']);stored['media']={'type':'reader','pages':[1,2],'total_pages':2};self.app.store(stored)
        with patch.object(self.app,'codex_generate',return_value=result):self.app.draft(fresh['id'],provider='codex')
        self.assertIsNone(self.app.preview(fresh['id'],{})['duplicate'])
        self.assertEqual(self.app.save(fresh['id'],{})['count'],3)
        self.assertTrue((self.vault/first['relative']).is_file())

    def test_interrupted_matching_files_do_not_block_the_review_save_button(self):
        c=self.prepared();rendered,selected,_=Editorial(self.app).render_all(c,{})
        c['save_intent']={'hashes':{r['relative']:hashlib.sha256(r['markdown'].encode()).hexdigest() for r in rendered.values()}};self.app.store(c)
        first=rendered[selected[0]];(self.vault/first['relative']).write_text(first['markdown'])
        self.assertEqual(self.app.preview(c['id'],{})['collisions'],[])
