import copy
import hashlib
import json
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from pathlib import Path
import test_editorial as base
from editorial import Editorial
from core import UserError
from jobs import Job,Cancelled,run_command,pending

class WorkflowTest(unittest.TestCase):
    setUp=base.EditorialTest.setUp;tearDown=base.EditorialTest.tearDown;collection=base.EditorialTest.collection;prepared=base.EditorialTest.prepared

    def fields(self,c):return {'notes':{},'selected_notes':['source',*[n['id'] for n in c['bundle']['notes']]],'active_note':'identidad'}
    def amendment(self):
        c=self.prepared();path='02_Cerebro/Tech_&_Codigo/nota_politica_previa.md';before='---\ntipo: nota_atomica\n---\n# Políticas\n\nUna identidad solicita permisos para acceder a un recurso.\n\nMI ANOTACIÓN PERSONAL.\n'
        (self.vault/path).write_text(before);self.app.handle({'action':'prepare_update','id':c['id'],'path':path})
        fields=self.fields(c);fields['notes']['identidad']={'save_mode':'append','target_path':path}
        review=self.app.preview(c['id'],fields);fields['notes']['identidad'].update(update_approved=True,update_review_hash=review['update']['review_hash'])
        return c,path,before,fields

    def test_partial_revision_preserves_other_sections_and_never_mutates_the_saved_draft(self):
        c=self.prepared();before='Prefacio personal\n\n## Primero\nTexto uno.\n\n## Segundo\nTexto dos y comentario personal.\n';fields=self.fields(c);fields['notes']['identidad']={'body':before}
        with patch.object(self.app,'codex_json',return_value={'body':'## Primero\nExplicación revisada.','_model':'test-model'}):
            proposal=self.app.handle({'action':'revise','id':c['id'],'note':'identidad','fields':fields,'section':'0','mode':'clarify'})
        self.assertTrue(proposal['after'].startswith('Prefacio personal\n\n'))
        self.assertTrue(proposal['after'].endswith('## Segundo\nTexto dos y comentario personal.\n'))
        self.assertEqual(self.app.load(c['id'])['bundle'],c['bundle'])

    def test_quotes_from_the_same_article_have_distinct_default_paths(self):
        paths=[]
        for text in ('Primera frase que merece conservarse.','Segunda frase distinta para estudiar.'):
            c=self.app.stage({'kind':'quote','title':'El mismo artículo','url':'https://example.org/article','text':text});self.app.draft(c['id'],provider='manual');paths.append(self.app.preview(c['id'],{})['relative'])
        self.assertNotEqual(*paths);self.assertTrue(all('_frase_' in p for p in paths))

    def test_revision_cannot_inject_unverified_links(self):
        c=self.prepared()
        with patch.object(self.app,'codex_json',return_value={'body':'Enlace [[inventado]]'}):
            with self.assertRaises(UserError):self.app.handle({'action':'revise','id':c['id'],'note':'identidad'})

    def test_integrated_note_keeps_source_pages_and_reroutes_links(self):
        c=self.prepared();f=self.fields(c);f.update(selected_notes=['source','identidad'],merged_into={'politicas':'identidad'});f['notes']['identidad']={'body':'## Integración\nIdentidad y políticas se explican conjuntamente.'}
        preview=self.app.preview(c['id'],f)
        self.assertIn('páginas 1–2',preview['markdown']);self.assertNotIn('nota_decidir_permisos',preview['markdown'])
        root=self.app.preview(c['id'],{**f,'active_note':'source'})['markdown'];self.assertEqual(root.count('nota_identidades_y_recursos|'),1)

    def test_internal_links_can_be_discarded_in_both_directions(self):
        c=self.prepared();f=self.fields(c);f['notes']['source']={'excluded_links':['identidad']}
        preview=self.app.preview(c['id'],f);self.assertNotIn('Síntesis y mapa',preview['markdown']);self.assertTrue(any(not v['accepted'] for v in preview['internal_links']))

    def test_append_requires_explicit_review_and_preserves_original_bytes(self):
        c,path,before,f=self.amendment();unchecked=copy.deepcopy(f);unchecked['notes']['identidad']['update_approved']=False
        with self.assertRaises(UserError):self.app.save(c['id'],unchecked)
        self.app.save(c['id'],f);after=(self.vault/path).read_text();self.assertTrue(after.startswith(before));self.assertIn('## Aporte:',after);self.assertEqual(after.count('MI ANOTACIÓN PERSONAL'),1)

    def test_changed_target_or_changed_proposal_invalidates_amendment_approval(self):
        c,path,before,f=self.amendment();f['notes']['identidad']['body']='Contenido cambiado después de aprobar.'
        with self.assertRaises(UserError):self.app.save(c['id'],f)
        (self.vault/path).write_text(before+'CAMBIO EXTERNO')
        with self.assertRaises(UserError):self.app.preview(c['id'],f)
        self.assertTrue((self.vault/path).read_text().endswith('CAMBIO EXTERNO'))

    def test_append_cannot_target_an_arbitrary_vault_path(self):
        c=self.prepared()
        with self.assertRaises(UserError):self.app.handle({'action':'prepare_update','id':c['id'],'path':'00_Sistema/MANUAL_VAULT.md'})

    def test_failed_mixed_publication_restores_amended_note_and_removes_new_notes(self):
        from core import write_new_atomic
        c,path,before,f=self.amendment();f['selected_notes']=['identidad','source','politicas'];calls=[]
        def fail(path,raw):
            calls.append(path)
            if len(calls)==3:raise OSError('Simulated write failure')
            return write_new_atomic(path,raw)
        with patch('editorial.write_new_atomic',side_effect=fail):
            with self.assertRaises(OSError):self.app.save(c['id'],f)
        self.assertEqual((self.vault/path).read_text(),before)
        self.assertFalse((self.vault/c['draft']['folder']/c['draft']['filename']).exists())

    def test_interrupted_amendment_resumes_without_adding_the_same_content_twice(self):
        from updates import digest
        c,path,before,f=self.amendment();stored=self.app.load(c['id']);rendered,selected,_=Editorial(self.app).render_all(stored,f)
        backup=self.app.state/'update-backups'/c['id']/(digest(path.encode())+'.bak');backup.parent.mkdir(parents=True);backup.write_text(before)
        stored['save_intent']={'hashes':{rendered[k]['relative']:digest(rendered[k]['markdown'].encode()) for k in selected},'updates':{path:digest(before.encode())},'date':None};self.app.store(stored)
        (self.vault/path).write_text(rendered['identidad']['markdown']);mtime=(self.vault/path).stat().st_mtime_ns
        self.assertEqual(self.app.preview(c['id'],f)['collisions'],[]);self.app.save(c['id'],f)
        self.assertEqual((self.vault/path).stat().st_mtime_ns,mtime);self.assertEqual((self.vault/path).read_text().count('## Aporte:'),1)

    def test_repeated_capture_cannot_append_the_same_source_to_the_same_target_twice(self):
        c,path,before,f=self.amendment();f['selected_notes']=['identidad'];f['notes']['identidad']['update_review_hash']=self.app.preview(c['id'],f)['update']['review_hash'];self.app.save(c['id'],f)
        fresh=self.prepared();self.app.handle({'action':'prepare_update','id':fresh['id'],'path':path})
        self.assertIsNotNone(self.app.preview(fresh['id'],f)['duplicate'])

    def test_cancel_flag_is_vault_scoped_and_a_worker_is_actually_stopped(self):
        identifier='a'*32;job=Job(self.app,identifier);job.start({'action':'upload_finish','upload':'b'*32});job.cancel()
        self.assertEqual(pending(self.app)[0]['action'],'upload_finish')
        started=time.monotonic()
        with self.assertRaises(Cancelled):run_command([sys.executable,'-c','import time;time.sleep(30)'],job.check)
        self.assertLess(time.monotonic()-started,2);request=job.resume();self.assertEqual(request['upload'],'b'*32);job.check()
        other=self.root/'Other';other.mkdir();self.app.set_config({'vault':str(other)})
        self.assertEqual(pending(self.app),[])
        with self.assertRaises(UserError):job.resume()

    def test_dismissed_jobs_stay_out_of_pending_and_cannot_resume(self):
        job=Job(self.app,'a'*32);job.start({'action':'video_url','url':'https://example.org/video'});job.update(status='failed')
        self.assertTrue(self.app.handle({'action':'discard_job','job':'a'*32})['discarded'])
        self.assertEqual(pending(self.app),[])
        self.assertEqual(Job(self.app,'a'*32).load()['status'],'discarded')
        with self.assertRaises(UserError):job.resume()

    def test_discard_capture_also_dismisses_its_failed_draft_without_affecting_other_jobs(self):
        c=self.prepared();job=Job(self.app,'a'*32);job.start({'action':'draft','id':c['id']});job.update(status='failed')
        other=Job(self.app,'b'*32);other.start({'action':'video_url','url':'https://example.org/other'});other.update(status='interrupted')
        result=self.app.handle({'action':'discard','id':c['id']})
        self.assertEqual(result['discarded_jobs'],['a'*32]);self.assertEqual(self.app.load(c['id'])['status'],'discarded')
        self.assertEqual([j['id'] for j in pending(self.app)],['b'*32])
        self.assertEqual(self.app.pending(),[])
        with self.assertRaises(UserError):job.resume()

    def test_active_jobs_and_their_captures_cannot_be_dismissed(self):
        c=self.prepared();job=Job(self.app,'a'*32);job.start({'action':'draft','id':c['id']})
        with self.assertRaises(UserError):self.app.handle({'action':'discard_job','job':'a'*32})
        with self.assertRaises(UserError):self.app.handle({'action':'discard','id':c['id']})
        self.assertEqual(self.app.load(c['id'])['status'],'draft');self.assertEqual(job.load()['status'],'running')
        with patch('jobs.os.kill',side_effect=ProcessLookupError):
            self.assertEqual(pending(self.app)[0]['status'],'interrupted')
            job.discard()
        self.assertEqual(pending(self.app),[])

    def test_cancellation_during_running_subprocess_terminates_it(self):
        calls=[]
        def check():
            calls.append(1)
            if len(calls)>2:raise Cancelled()
        started=time.monotonic()
        with self.assertRaises(Cancelled):run_command([sys.executable,'-c','import time;time.sleep(30)'],check)
        self.assertLess(time.monotonic()-started,2)
