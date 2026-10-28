from pathlib import Path
from unittest.mock import patch
import test_core as base
import test_editorial as editorial_base
from editorial import Editorial
from core import UserError


class DeletedNotesTest(base.unittest.TestCase):
    setUp = base.CoreTest.setUp
    tearDown = base.CoreTest.tearDown
    capture = base.CoreTest.capture
    prepared = base.CoreTest.prepared

    def test_regenerated_note_can_be_saved_after_original_was_deleted(self):
        original, _ = self.prepared()
        saved = self.app.save(original['id'], {})
        regenerated, _ = self.prepared()
        self.assertEqual(self.app.preview(regenerated['id'], {})['duplicate'], saved['relative'])
        Path(saved['path']).unlink()
        self.assertIsNone(self.app.preview(regenerated['id'], {})['duplicate'])
        recreated = self.app.save(regenerated['id'], {})
        self.assertTrue(Path(recreated['path']).is_file())
        self.assertEqual(self.app.db.execute('SELECT count(*) FROM saves').fetchone()[0], 1)
        again, _ = self.prepared()
        with self.assertRaises(UserError):
            self.app.save(again['id'], {})

    def test_missing_original_does_not_allow_overwriting_a_different_existing_note(self):
        original, _ = self.prepared()
        saved = self.app.save(original['id'], {})
        Path(saved['path']).unlink()
        regenerated, proposal = self.prepared()
        filename = 'fuente_ocupada.md'
        destination = self.vault / proposal['draft']['folder'] / filename
        destination.write_text('Personal notes')
        with self.assertRaises(UserError):
            self.app.save(regenerated['id'], {'filename': filename})
        self.assertEqual(destination.read_text(), 'Personal notes')

    def test_stale_history_is_replaced_only_when_the_new_note_is_published(self):
        original, _ = self.prepared()
        saved = self.app.save(original['id'], {})
        Path(saved['path']).unlink()
        regenerated, _ = self.prepared()
        row = self.app.db.execute('SELECT * FROM saves').fetchone()
        self.assertIsNone(self.app.preview(regenerated['id'], {})['duplicate'])
        self.assertEqual(self.app.db.execute('SELECT * FROM saves').fetchone(), row)
        with patch('core.write_new_atomic', side_effect=OSError('Disk unavailable')):
            with self.assertRaises(OSError):
                self.app.save(regenerated['id'], {})
        self.assertEqual(self.app.db.execute('SELECT * FROM saves').fetchone(), row)

    def test_collection_recreation_and_partial_deletion_keep_collision_protection(self):
        def collection():
            c, result = editorial_base.EditorialTest.collection(self)
            with patch.object(self.app, 'codex_generate', return_value=result):
                self.app.draft(c['id'], provider='codex')
            return c
        original = collection(); saved = self.app.save(original['id'], {})
        regenerated = collection()
        (self.vault / saved['relative']).unlink()
        preview = self.app.preview(regenerated['id'], {})
        self.assertTrue(preview['collisions'])
        with self.assertRaises(UserError):
            self.app.save(regenerated['id'], {})
        for path in saved['paths']:
            (self.vault / path).unlink(missing_ok=True)
        self.assertIsNone(self.app.preview(regenerated['id'], {})['duplicate'])
        recreated = self.app.save(regenerated['id'], {})
        self.assertEqual(recreated['count'], 3)
        self.assertTrue(all((self.vault / path).is_file() for path in recreated['paths']))
