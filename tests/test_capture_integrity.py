"""Long captures must not silently lose content or share a prefix-only identity."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'native'))
from core import UserError
from media import Media
import test_core as core_tests


class CaptureIntegrityTest(unittest.TestCase):
    setUp = core_tests.CoreTest.setUp
    tearDown = core_tests.CoreTest.tearDown
    capture = core_tests.CoreTest.capture

    def test_manual_capture_preserves_the_end_through_save(self):
        text = 'Contenido original. ' * 4500 + 'FINAL_INTACTO'
        c = self.capture(text=text)
        result = self.app.draft(c['id'], provider='manual')
        self.assertTrue(result['draft']['body'].endswith('FINAL_INTACTO'))
        saved = self.app.save(c['id'], {})
        self.assertIn(text, Path(saved['path']).read_text())

    def test_oversized_manual_capture_is_rejected_and_retained(self):
        text = 'A' * 120000 + 'FINAL_INTACTO'
        c = self.capture(text=text)
        with self.assertRaises(UserError):
            self.app.draft(c['id'], provider='manual')
        stored = self.app.load(c['id'])
        self.assertEqual(stored['text'], text)
        self.assertEqual(stored['status'], 'pending')
        self.assertNotIn('draft', stored)
        self.assertEqual(list(self.vault.rglob('*.md')), [])

    def test_ordinary_capture_reports_its_ingestion_limit(self):
        c = self.capture(text='A' * 170000)
        self.assertEqual(len(c['text']), 160000)
        self.assertTrue(c['warnings'])

    def transcript(self, tail):
        return Media(self.app).transcript_capture(
            [{'start': 0, 'text': 'T' * 150100 + tail}], 'Long source',
            'local-file:long.vtt', 'fixture')

    def test_transcript_identity_covers_the_end_and_is_repeatable(self):
        a, b, repeated = self.transcript(' END_A'), self.transcript(' END_B'), self.transcript(' END_A')
        self.assertNotEqual(a['fingerprint'], b['fingerprint'])
        self.assertEqual(a['fingerprint'], repeated['fingerprint'])
        self.assertEqual(a['fingerprint_version'], 2)

    def test_old_saved_transcript_matches_only_if_full_content_matches(self):
        original = self.transcript(' END_A')
        stored = self.app.load(original['id'])
        legacy = stored.get('legacy_fingerprint', stored['fingerprint'])
        stored.update(fingerprint=legacy, status='saved', saved_path='02_Cerebro/Modelos_Mentales/old.md')
        stored.pop('fingerprint_version', None)
        stored.pop('legacy_fingerprint', None)
        self.app.store(stored)
        (self.vault / stored['saved_path']).write_text('# Original saved note\n')
        self.app.db.execute('INSERT INTO saves VALUES (?,?,?)', (legacy, stored['saved_path'], '2026-01-01'))
        self.app.db.commit()
        same, different = self.transcript(' END_A'), self.transcript(' END_B')
        self.assertEqual(self.app.duplicate(same), stored['saved_path'])
        self.assertIsNone(self.app.duplicate(different))

    def test_existing_pending_and_recovery_records_are_not_rewritten_on_load(self):
        c = self.transcript(' LEGACY')
        stored = self.app.load(c['id'])
        stored['fingerprint'] = stored.pop('legacy_fingerprint')
        stored.pop('fingerprint_version')
        stored['save_intent'] = {'hashes': {'note.md': 'existing'}, 'date': '2026-01-01'}
        self.app.store(stored)
        path = self.app.state / 'captures' / (c['id'] + '.json')
        before = path.read_bytes()
        self.app.load(c['id'])
        self.assertEqual(path.read_bytes(), before)
