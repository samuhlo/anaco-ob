import base64
import json
from unittest.mock import patch
import test_core as core_tests
from core import UserError
from reader import Reader


class ReaderTest(core_tests.unittest.TestCase):
    setUp = core_tests.CoreTest.setUp
    tearDown = core_tests.CoreTest.tearDown

    def book(self, count=55, omit=None):
        reader = Reader(self.app)
        job = reader.begin({'count': count, 'url': 'https://course.example/book', 'title': 'Libro de cloud', 'identity': 'snapshot'})['job']
        data = base64.b64encode(core_tests.PNG).decode()
        for index in range(1, count + 1):
            if index == omit:
                continue
            text = f'Contenido exclusivo de la página {index}. ' + ('Las políticas determinan qué acciones pueden realizar las identidades sobre los recursos. ' * 3)
            reader.page_begin({'job': job, 'index': index, 'size': len(core_tests.PNG), 'text': text})
            reader.chunk({'job': job, 'index': index, 'offset': 0, 'data': data})
            reader.page_finish({'job': job, 'index': index})
        return reader, job

    def fake_generation(self, calls, fail_at=None):
        original = self.app.codex_generate
        def fake(capture, candidates, folders):
            if capture.get('reader', {}).get('job'):
                return original(capture, candidates, folders)
            scope = capture['reader']['scope']
            pages = capture['reader'].get('pages', [])
            calls.append((scope, pages, capture['text']))
            if fail_at and scope == 'batch' and pages[0] == fail_at:
                raise UserError('Lectura interrumpida')
            body = capture['text'] if scope == 'synthesis' else '\n'.join(f'Aprendido en la página {n}.' for n in pages)
            return {'title': 'Libro de cloud', 'context': 'Estudio del libro completo', 'body': body,
                    'folder': folders[0], 'tags': ['cloud'], 'relations': [], '_model': 'gpt-6.1-sol' if scope == 'batch' else 'gpt-6-luna',
                    'image_captions': [{'index': i, 'description': f"Diagrama de la página {image['page']} del libro.", 'useful': True} for i, image in enumerate(capture['images'])]}
        return fake

    def test_all_55_pages_are_captured_and_read_in_batches_before_synthesis(self):
        reader, job = self.book()
        c = reader.finish({'job': job})
        self.assertEqual(c['reader']['captured_pages'], 55)
        self.assertLessEqual(len(c['images']), 6)
        self.assertIn('página 55.', self.app.load(c['id'])['text'])
        calls = []
        with patch.object(self.app, 'codex_generate', side_effect=self.fake_generation(calls)):
            self.app.draft(c['id'], provider='codex')
            self.app.draft(c['id'], provider='codex')
        batches = [call for call in calls if call[0] == 'batch']
        self.assertEqual([n for _, pages, _ in batches for n in pages], list(range(1, 56)))
        self.assertEqual(len(batches), 10)  # Repeated preparation reuses the completed reading.
        syntheses = [call for call in calls if call[0] == 'synthesis']
        self.assertEqual(len(syntheses), 2)
        self.assertIn('Aprendido en la página 55.', syntheses[0][2])
        self.assertEqual(self.app.load(c['id'])['reader']['analyzed_pages'], 55)

    def test_missing_page_cannot_finish_as_a_complete_book_and_can_resume(self):
        reader, job = self.book(55, omit=27)
        with self.assertRaisesRegex(UserError, 'incompleto'):
            reader.finish({'job': job})
        resumed = reader.begin({'job': job, 'count': 55, 'url': 'https://course.example/book', 'identity': 'snapshot'})
        self.assertEqual(len(resumed['done']), 54)
        self.assertNotIn(27, resumed['done'])
        reader.page_begin({'job': job, 'index': 27, 'size': 0, 'text': 'Página veintisiete recuperada.'})
        reader.page_finish({'job': job, 'index': 27})
        self.assertEqual(reader.finish({'job': job})['reader']['captured_pages'], 55)

    def test_editorial_profile_change_reuses_completed_reading_and_keeps_the_new_cache(self):
        reader,job=self.book(7);c=reader.finish({'job':job});calls=[]
        with patch.object(self.app,'codex_generate',side_effect=self.fake_generation(calls)):
            self.app.draft(c['id'],provider='codex')
        original_profile=self.app.guide;profile=original_profile();profile['hash']='updated-editorial-guidance'
        calls=[]
        with patch.object(self.app,'guide',return_value=profile),patch.object(self.app,'codex_generate',side_effect=self.fake_generation(calls)):
            self.app.draft(c['id'],provider='codex')
            self.app.draft(c['id'],provider='codex')
        self.assertEqual([scope for scope,_,_ in calls],['synthesis','synthesis'])

    def test_failed_batch_keeps_previous_reading_without_claiming_completion(self):
        reader, job = self.book(18)
        c = reader.finish({'job': job})
        calls = []
        with patch.object(self.app, 'codex_generate', side_effect=self.fake_generation(calls, fail_at=13)):
            with self.assertRaisesRegex(UserError, 'interrumpida'):
                self.app.draft(c['id'], provider='codex')
        self.assertNotIn('analyzed_pages', self.app.load(c['id'])['reader'])
        calls = []
        with patch.object(self.app, 'codex_generate', side_effect=self.fake_generation(calls)):
            self.app.draft(c['id'], provider='codex')
        self.assertEqual([pages for scope, pages, _ in calls if scope == 'batch'], [[13, 14, 15, 16, 17, 18]])
        self.assertEqual(self.app.load(c['id'])['reader']['analyzed_pages'], 18)

    def test_cross_vault_job_and_changed_snapshot_are_rejected(self):
        reader, job = self.book(1)
        with self.assertRaisesRegex(UserError, 'cambió'):
            reader.begin({'job': job, 'count': 1, 'url': 'https://course.example/book', 'identity': 'different'})
        other = self.root / 'Other'; other.mkdir()
        self.app.set_config({'vault': str(other)})
        with self.assertRaisesRegex(UserError, 'otro vault'):
            reader.finish({'job': job})

    def test_corrupt_chunks_and_incomplete_pages_are_rejected(self):
        reader = Reader(self.app)
        job = reader.begin({'count': 1, 'url': 'https://course.example/book'})['job']
        reader.page_begin({'job': job, 'index': 1, 'size': 10, 'text': 'Contenido'})
        with self.assertRaises(UserError):
            reader.chunk({'job': job, 'index': 1, 'offset': 4, 'data': 'AA=='})
        with self.assertRaises(UserError):
            reader.page_finish({'job': job, 'index': 1})
